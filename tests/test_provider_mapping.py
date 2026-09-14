from datetime import UTC, datetime
from types import SimpleNamespace as NS

from gcp_dash.gcp.provider import (
    bucket_from_api,
    firewall_from_api,
    instance_from_api,
    network_from_api,
    project_from_api,
    subnetwork_from_api,
)


def test_instance_mapping_shortens_urls_and_picks_ips():
    api = NS(
        name="vm-1",
        zone="https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-a",
        machine_type="https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-a/machineTypes/e2-small",
        status="RUNNING",
        network_interfaces=[NS(network_i_p="10.0.0.2", access_configs=[NS(nat_i_p="34.1.2.3")])],
    )
    inst = instance_from_api(api)
    assert inst.name == "vm-1"
    assert inst.zone == "us-central1-a"
    assert inst.machine_type == "e2-small"
    assert inst.status == "RUNNING"
    assert inst.internal_ip == "10.0.0.2"
    assert inst.external_ip == "34.1.2.3"


def test_instance_mapping_without_nics():
    inst = instance_from_api(NS(name="x", zone="", machine_type="", status="TERMINATED", network_interfaces=[]))
    assert inst.internal_ip is None and inst.external_ip is None


def test_bucket_mapping():
    b = bucket_from_api(
        NS(name="b1", location="US", storage_class="STANDARD",
           time_created=datetime(2024, 1, 2, tzinfo=UTC))
    )
    assert b.name == "b1" and b.location == "US" and b.storage_class == "STANDARD"
    assert b.created == "2024-01-02T00:00:00+00:00"


def test_network_mapping():
    n = network_from_api(
        NS(name="default", auto_create_subnetworks=True, subnetworks=["a", "b"],
           routing_config=NS(routing_mode="REGIONAL"))
    )
    assert n.name == "default" and n.auto_subnets is True
    assert n.subnet_count == 2 and n.routing_mode == "REGIONAL"


def test_subnetwork_mapping():
    s = subnetwork_from_api(
        NS(name="sub", region=".../regions/us-east1", network=".../networks/default",
           ip_cidr_range="10.10.0.0/20", private_ip_google_access=True)
    )
    assert s.region == "us-east1" and s.network == "default" and s.cidr == "10.10.0.0/20"
    assert s.private_google_access is True


def test_firewall_mapping_allow():
    f = firewall_from_api(
        NS(name="allow-ssh", network=".../networks/default", direction="INGRESS", priority=1000,
           allowed=[NS(I_p_protocol="tcp", ports=["22"])], denied=[],
           source_ranges=["0.0.0.0/0"], target_tags=["ssh"])
    )
    assert f.action == "allow" and f.rules == "tcp:22"
    assert f.source_ranges == ["0.0.0.0/0"] and f.target_tags == ["ssh"]


def test_firewall_mapping_deny_all():
    f = firewall_from_api(
        NS(name="deny", network="n", direction="EGRESS", priority=65534,
           allowed=[], denied=[NS(I_p_protocol="all", ports=[])], source_ranges=[], target_tags=[])
    )
    assert f.action == "deny" and f.rules == "all"


def test_project_mapping():
    p = project_from_api(NS(project_id="my-proj", display_name="My Proj", name="projects/123",
                            state=NS(name="ACTIVE")))
    assert p.project_id == "my-proj" and p.number == "123" and p.state == "ACTIVE"
