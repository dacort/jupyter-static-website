from aws_cdk import (
    core as cdk,
    aws_certificatemanager as acm,
)

class CloudfrontCertificateStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, domain_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id,  **kwargs)

        cert = acm.Certificate(
            self,
            "mySiteCert",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(),
        )

        cdk.CfnOutput(self, "certificate_arn", value=cert.certificate_arn)