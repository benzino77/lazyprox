import json
from pathlib import Path
from typing import Literal
from copy import deepcopy

from proxmoxer import ProxmoxAPI

from lazyprox.common import Config


class _ProxmoxData():
    def __init__(self):
        self.p_prox_resources: dict = {}

    def initialize(self) -> None:
        cfg = Config.configuration.get("server")[Config.server_index]

        self.prox: ProxmoxAPI = ProxmoxAPI(cfg["host"], user=f"{cfg['user']}@{cfg['realm']}",
                                           token_name=cfg["token_name"], token_value=cfg["token_value"], verify_ssl=cfg.get("verify_ssl", True))
        # clear current data, we will be collecting new data based on new ProxmoxAPI
        self.p_prox_resources = {}

    def refresh_api_information(self, api: str) -> None:
        # if the api is not rrddata, we just getting that data without API call parameters
        info = None
        if api.find("rrddata") == -1:
            info = self.prox(api).get()
        else:
            rrddata_timeframe = Config.configuration.get(
                "application").get("rrddata_timeframe")
            rrddata_cf = Config.configuration.get(
                "application").get("rrddata_cf")
            info = self.prox(api).get(timeframe=rrddata_timeframe,
                                      cf=rrddata_cf)
        self.p_prox_resources[api] = info

    def get_node_information(self, node_name: str) -> dict:
        nodes: list = self.p_prox_resources.get("nodes", [])
        node_info = {}
        for node in nodes:
            if node["node"] == node_name:
                node_info = deepcopy(node)
                node_info["full_status"] = self.p_prox_resources.get(
                    f"nodes/{node_name}/status")
                node_info["rrddata"] = self.p_prox_resources.get(
                    f"nodes/{node_name}/rrddata")
                break

        return node_info

    def get_guest_information(self, node_name: str, type: Literal["lxc", "qemu"], vmid: str) -> dict:
        guest_info = {}
        for g in self.p_prox_resources.get(
                f"nodes/{node_name}/{type}", []):
            if g["vmid"] == int(vmid):
                guest_info = deepcopy(g)
                break

        if not guest_info:
            return {}

        guest_info["node"] = node_name
        guest_info["status/current"] = self.p_prox_resources.get(
            f"nodes/{node_name}/{type}/{vmid}/status/current", {})
        guest_info["rrddata"] = self.p_prox_resources.get(
            f"nodes/{node_name}/{type}/{vmid}/rrddata", {})

        return guest_info

    def get_guests_list(self, resource_type: Literal["qemu", "lxc"]) -> list:
        """
        Getting quests list of the given type on the proxmox
        """
        nodes: list = self.p_prox_resources.get("nodes", [])
        vms: list = []
        for node in nodes:
            resources_key: str = f"nodes/{node['node']}/{resource_type}"
            vms_on_node: list = self.p_prox_resources.get(
                resources_key, [])
            # filter out resources which are templates
            vms_on_node = [
                vm for vm in vms_on_node if vm.get("template", 0) != 1]
            # add node information to each lxc
            vms_on_node = [
                {**vm,
                 "node": node["node"],
                 "status/current": self.p_prox_resources.get(f"{resources_key}/{vm['vmid']}/status/current", {}),
                 "rrddata": self.p_prox_resources.get(f"{resources_key}/{vm['vmid']}/rrddata", [])} for vm in vms_on_node]
            vms.extend(vms_on_node)
        return vms

    def dump_resources(self) -> Path:
        """Dump all resources to file"""
        dest: Path = Path(Config.configuration.get("application").get(
            "debug_dump_dest"))

        with dest.open("w") as f:
            json.dump(self.p_prox_resources, f)

        return dest


ProxmoxData = _ProxmoxData()
