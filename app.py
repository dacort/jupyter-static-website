from aws_cdk import core as cdk
from cloudfront_certificate_stack import CloudfrontCertificateStack

from emr_studio_publisher.emr_studio_publisher_stack import EmrStudioPublisherStack


app = cdk.App()

# If we pass in a domain name, we want to provision a seperate certificate
# stack with that domain name.
#
# If we pass in nothing OR a domain name *and* a cert_arn,
# then we can provision the publisher stack.
domain_name = app.node.try_get_context("domain_name")
certificate_arn = app.node.try_get_context("certificate_arn")

# This stack must be provisioned before the StudioPublisher stack if we
# wish to tie a custom domain name to our Cloudfront distribution.
if domain_name and not certificate_arn:
    CloudfrontCertificateStack(
        app,
        "CloudfrontCertificateStack",
        domain_name,
        env=cdk.Environment(region="us-east-1"),
    )


if all([domain_name, certificate_arn]) or not all([domain_name, certificate_arn]):
    EmrStudioPublisherStack(
        app,
        "EmrStudioPublisherStack",
        domain_name=domain_name,
        certificate_arn=certificate_arn,
    )

app.synth()
