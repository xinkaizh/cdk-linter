import logging
from typing import Any, override

from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_graph import ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.cfn.resource_type import ResourceType
from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.rules.rule import CfnRule

logger = logging.getLogger(__name__)


class Ec2InstanceVpcRule(CfnRule):
    description = "Checks if EC2 instances are placed in a VPC subnet"

    @override
    def check(self, graph: ResourceGraph, index: ResourceIndex) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        instances = index.get_resources_by_type(ResourceType.EC2_INSTANCE)

        for instance in instances:
            subnet_ids = self._extract_subnet_ids(instance.properties)

            if not subnet_ids:
                diagnostics.append(
                    Diagnostic(
                        message=(
                            f"EC2 instance {instance.id} must belong to a VPC by "
                            "referencing a subnet"
                        )
                    )
                )
                continue

            for subnet_id in subnet_ids:
                subnet = index.get_resource_by_id(subnet_id)
                if subnet is None or subnet.type != ResourceType.SUBNET:
                    diagnostics.append(
                        Diagnostic(
                            message=(
                                f"EC2 instance {instance.id} references subnet "
                                f"{subnet_id}, but that subnet is not defined"
                            )
                        )
                    )
                    continue

                vpc_id = self._extract_ref(subnet.properties.get("VpcId"))
                if vpc_id is None:
                    diagnostics.append(
                        Diagnostic(
                            message=(
                                f"EC2 instance {instance.id} uses subnet {subnet.id}, "
                                "but the subnet does not reference a VPC"
                            )
                        )
                    )
                    continue

                vpc = index.get_resource_by_id(vpc_id)
                if vpc is None or vpc.type != ResourceType.VPC:
                    diagnostics.append(
                        Diagnostic(
                            message=(
                                f"EC2 instance {instance.id} uses subnet {subnet.id}, "
                                f"but VPC {vpc_id} is not defined"
                            )
                        )
                    )

        if instances and not diagnostics:
            logger.info("EC2/VPC check passed: all EC2 instances are placed in a VPC subnet")

        return diagnostics

    def _extract_subnet_ids(self, properties: dict[str, Any]) -> list[str]:
        subnet_ids: list[str] = []

        subnet_id = self._extract_ref(properties.get("SubnetId"))
        if subnet_id is not None:
            subnet_ids.append(subnet_id)

        for interface in properties.get("NetworkInterfaces", []):
            if not isinstance(interface, dict):
                continue
            subnet_id = self._extract_ref(interface.get("SubnetId"))
            if subnet_id is not None:
                subnet_ids.append(subnet_id)

        return subnet_ids

    def _extract_ref(self, value: Any) -> str | None:
        if isinstance(value, dict) and isinstance(value.get("Ref"), str):
            return value["Ref"]
        return None
