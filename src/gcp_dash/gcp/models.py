from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Project:
    project_id: str
    display_name: str
    number: str
    state: str


@dataclass(frozen=True)
class Instance:
    name: str
    zone: str
    machine_type: str
    status: str
    internal_ip: str | None
    external_ip: str | None


@dataclass(frozen=True)
class Bucket:
    name: str
    location: str
    storage_class: str
    created: str | None


@dataclass(frozen=True)
class Network:
    name: str
    auto_subnets: bool
    subnet_count: int
    routing_mode: str


@dataclass(frozen=True)
class Subnetwork:
    name: str
    region: str
    network: str
    cidr: str
    private_google_access: bool


@dataclass(frozen=True)
class FirewallRule:
    name: str
    network: str
    direction: str
    priority: int
    action: str
    rules: str
    source_ranges: list[str] = field(default_factory=list)
    target_tags: list[str] = field(default_factory=list)
