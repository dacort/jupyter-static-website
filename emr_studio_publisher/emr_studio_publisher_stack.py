import os
from aws_cdk import (
    core as cdk,
    aws_s3 as s3,
    aws_s3_assets as s3a,
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_servicecatalog as servicecatalog,
)


class ServiceCatalogOutput:
    def __init__(
        self,
    ) -> None:
        pass


class EmrStudioPublisherStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        *,
        domain_name: str = None,
        certificate_arn: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a centralized bucket for all our logging
        log_bucket = s3.Bucket(
            self,
            "notebook-log-bucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Create a website bucket
        notebook_website_bucket = s3.Bucket(
            self,
            "notebook-bucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            server_access_logs_bucket=log_bucket,
            server_access_logs_prefix="logs/s3/",
        )

        # Upload the initial version of the site repository to the website bucket
        artifacts_path = os.path.join(os.path.dirname(__file__), "..", "code_bootstrap")
        repo_artifact = s3a.Asset(
            self, "repo-artifact", path=os.path.normpath(artifacts_path)
        )

        # Create a CloudFront function to redirect subdirectories to index.html
        cf_function = cloudfront.Function(
            self,
            "index_redirect",
            comment="Index redirector",
            code=cloudfront.FunctionCode.from_inline(
                """
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // Check whether the URI is missing a file name.
    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    } 
    // Check whether the URI is missing a file extension.
    else if (!uri.includes('.')) {
        request.uri += '/index.html';
    }

    return request;
}
"""
            ),
        )

        if certificate_arn is not None:
            my_certificate = acm.Certificate.from_certificate_arn(
                self, "domain-cert", certificate_arn
            )
        else:
            my_certificate = None

        # Create a CloudFront distribution for our website bucket
        distribution = cloudfront.Distribution(
            self,
            "www-s3-notebooks",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(notebook_website_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                function_associations=[
                    {
                        "function": cf_function,
                        "eventType": cloudfront.FunctionEventType.VIEWER_REQUEST,
                    }
                ],
            ),
            default_root_object="index.html",
            log_bucket=log_bucket,
            log_file_prefix="logs/cloudfront/",
            enable_logging=True,
            domain_names=list(filter(None, [domain_name])),
            certificate=my_certificate,
        )
        cdk.CfnOutput(
            self, "cloudfront-endpoint", value=f"https://{distribution.domain_name}"
        )

        # EMR Studio can use service catalog templates to deploy clusters.
        # That is disabled in this version of the stack.
        # svc_cat_prod = self.create_service_catalog_template("arn:aws:iam::111122223333:role/EMRStudio-EMRStudioUserRole230891F0-GK7R75XW85LU")

        # Create a CodeCommit repo for our website
        # We use `CfnRepository` so that we can pre-populate with an initial site.
        # Other methods below expect a `codecommit.Repository``, so we create the construct from the cfn one.
        repo2 = codecommit.CfnRepository(
            self,
            "data-team-repo-cfn",
            repository_name="windycity-notebooks",
            repository_description="Our publicy shared notebooks",
            code=codecommit.CfnRepository.CodeProperty(
                s3=codecommit.CfnRepository.S3Property(
                    bucket=repo_artifact.s3_bucket_name,
                    key=repo_artifact.s3_object_key,
                ),
                branch_name="main",
            ),
        )
        repo = codecommit.Repository.from_repository_arn(
            self, "data-team-repo", repo2.attr_arn
        )

        # Now we create a codebuild project that builds our mkdocs site
        mkdocs_build_project = codebuild.Project(
            self,
            "mkdocs-build",
            source=codebuild.Source.code_commit(repository=repo),
            build_spec=codebuild.BuildSpec.from_source_filename("site/buildspec.yml"),
        )

        # Now let's build a codepipeline that can:
        # - Build the static website from the source code
        # - Copy the resulting artifact to S3
        source_artifact = codepipeline.Artifact("SourceArtifact")
        build_artifact = codepipeline.Artifact("BuildArtifact")
        code_source = codepipeline_actions.CodeCommitSourceAction(
            output=source_artifact, repository=repo, branch="main", action_name="Source"
        )

        cp_build = codepipeline_actions.CodeBuildAction(
            input=source_artifact,
            action_name="Build",
            project=mkdocs_build_project,
            outputs=[build_artifact],
        )
        s3_website_deploy = codepipeline_actions.S3DeployAction(
            bucket=notebook_website_bucket,
            extract=True,
            action_name="WebsiteDeploy",
            input=build_artifact,
        )
        # - (disabled) Deploy any cluster templates to Service Catalog
        # sc_deploy = codepipeline_actions.ServiceCatalogDeployActionBeta1(
        #     product_id="prod-unzapsuxmjhmk",
        #     product_version_name="v1.0.0",
        #     template_path=source_artifact.at_path("/cfn/docker-cluster.yaml"),
        #     action_name="Deploy",
        # )

        website_pipeline = codepipeline.Pipeline(
            self,
            "service-catalog-pipeline",
            stages=[
                codepipeline.StageProps(stage_name="Source", actions=[code_source]),
                codepipeline.StageProps(stage_name="Build", actions=[cp_build]),
                codepipeline.StageProps(
                    stage_name="Deploy", actions=[s3_website_deploy]
                ),
            ],
        )

    def create_service_catalog_template(
        self, user_role_arn: str
    ) -> ServiceCatalogOutput:
        ## Now it's time for service catalog stuff
        sc_role = iam.Role(
            self,
            "EMRStudioClusterTemplateLaunchRole",
            assumed_by=iam.ServicePrincipal("servicecatalog.amazonaws.com"),
        )
        sc_policy = iam.ManagedPolicy(
            self,
            "EMRStudioClusterTemplatePolicy",
            roles=[sc_role],
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "cloudformation:CreateStack",
                            "cloudformation:DeleteStack",
                            "cloudformation:DescribeStackEvents",
                            "cloudformation:DescribeStacks",
                            "cloudformation:GetTemplateSummary",
                            "cloudformation:SetStackPolicy",
                            "cloudformation:ValidateTemplate",
                            "cloudformation:UpdateStack",
                            "elasticmapreduce:RunJobFlow",
                            "elasticmapreduce:DescribeCluster",
                            "elasticmapreduce:TerminateJobFlows",
                            "servicecatalog:*",
                            "s3:GetObject",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=["iam:PassRole"],
                        resources=[
                            f"arn:aws:iam::{cdk.Aws.ACCOUNT_ID}:role/EMR_DefaultRole",
                            f"arn:aws:iam::{cdk.Aws.ACCOUNT_ID}:role/EMR_EC2_DefaultRole",
                        ],
                    ),
                ]
            ),
        )

        sc_portfolio = servicecatalog.CfnPortfolio(
            self,
            "EMRStudioClusterTemplatePortfolio",
            display_name="ClusterTemplatePortfolio",
            provider_name="emr-studio-examples",
        )
        sc_portfolio_assoction = servicecatalog.CfnPortfolioPrincipalAssociation(
            self,
            "EMRStudioClusterTemplatePortfolioPrincipalAssociationForEndUser",
            principal_arn=user_role_arn,
            portfolio_id=sc_portfolio.ref,
            principal_type="IAM",
        )
        sc_portfolio_assoction.node.add_dependency(sc_portfolio)

        basemap_cluster = servicecatalog.CfnCloudFormationProduct(
            self,
            "EMRStudioBasemapProduct",
            name="matplotlib-cluster",
            description="An emr-6.2.0 cluster that has matplotlib pre-installed.",
            owner="emr-studio-examples",
            provisioning_artifact_parameters=[
                servicecatalog.CfnCloudFormationProduct.ProvisioningArtifactPropertiesProperty(
                    name="Matplotlib Cluster Template",
                    description="Matplotlib Cluster Template",
                    info={
                        "LoadTemplateFromURL": "https://gist.githubusercontent.com/dacort/14466352d025c7fcdeafda438de1384b/raw/17a2e8980b5629c390155a65116cec9f056bda31/matplotlib-cluster.yaml"
                    },
                )
            ],
        )
        sc_productassoc = servicecatalog.CfnPortfolioProductAssociation(
            self,
            "EMRStudioBasemapProductPortfolioMapping",
            portfolio_id=sc_portfolio.ref,
            product_id=basemap_cluster.ref,
        )

        sc_productassoc.node.add_dependency(sc_portfolio)
        sc_productassoc.node.add_dependency(basemap_cluster)

        sc_constraint = servicecatalog.CfnLaunchRoleConstraint(
            self,
            "EMRStudioPortfolioLaunchRoleConstraint",
            portfolio_id=sc_portfolio.ref,
            product_id=basemap_cluster.ref,
            role_arn=sc_role.role_arn,
        )
        sc_constraint.node.add_dependency(sc_portfolio)
        sc_constraint.node.add_dependency(basemap_cluster)

        return ServiceCatalogOutput()
