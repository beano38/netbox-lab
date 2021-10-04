import pynetbox
import oyaml as yaml

from config import NETBOX_URL, NETBOX_TOKEN

# Instantiate pynetbox.api class with URL of your NETBOX and your API TOKEN
nb = pynetbox.api(url=NETBOX_URL, token=NETBOX_TOKEN)


def interconnect(site_slug, role_slug, a_interface, a_device, z_interface, z_device):
    # Query Prefixes for right site and role
    parent_pfx = nb.ipam.prefixes.filter(site=site_slug, role=role_slug)
    if len(parent_pfx) > 1:
        # ***************Do something about this later***************
        print(parent_pfx)

    # Create next available /30 prefix
    interconnect_pfx = parent_pfx[0].available_prefixes.create(
        {
            "prefix_length": 30,
            "site": {"slug": site_slug},
            "role": {"slug": "interconnect"},
            "is_pool": False,
        }
    )

    # Set IP addresses
    a_ip = interconnect_pfx.available_ips.list()[0]
    z_ip = interconnect_pfx.available_ips.list()[1]

    # Set interfaces
    # ***************Check if interface exists first, create if needed***************
    a_int = nb.dcim.interfaces.get(name=a_interface, device=a_device)
    z_int = nb.dcim.interfaces.get(name=z_interface, device=z_device)

    # Assign IP addresses
    a_assign = nb.ipam.ip_addresses.create(
        {
            "address": a_ip.address,
            "status": "active",
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": a_int.id
        }
    )
    z_assign = nb.ipam.ip_addresses.create(
        {
            "address": z_ip.address,
            "status": "active",
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": z_int.id
        }
    )

    # Connect interfaces
    # ***************Check if cable exists first, create if needed***************
    connection = nb.dcim.cables.create(
        {
            "termination_a_type": "dcim.interface",
            "termination_a_id": a_int.id,
            "termination_b_type": "dcim.interface",
            "termination_b_id": z_int.id,
            "type": "cat6",
            "status": "connected",
        }
    )

    ipv4_address_a = a_ip.address.split("/")[0]
    ipv4_address_z = z_ip.address.split("/")[0]

    output = {"a_ip_address": ipv4_address_a, "z_ip_address": ipv4_address_z}

    return output


def write_yaml(site_slug, role_slug, a_interface, a_device, z_interface, z_device):
    info = interconnect(site_slug=site_slug, role_slug=role_slug, a_device=a_device, z_device=z_device, a_interface=a_interface, z_interface=z_interface)
    int_a = a_interface.split("Ethernet")[1]
    int_z = a_interface.split("Ethernet")[1]

    stuff = [
        {
            "name": "{}-{}".format(a_device, z_device),
            "device-interfaces": [
                {
                    "device": a_device,
                    "intf-number": int_a,
                    "description": "to {} - {}".format(z_device, z_interface),
                    "ipv4_address": info['a_ip_address'],
                    "ipv4_mask": "255.255.255.252"
                },
                {
                    "device": z_device,
                    "intf-number": int_z,
                    "description": "to {} - {}".format(a_device, a_interface),
                    "ipv4_address": info['z_ip_address'],
                    "ipv4_mask": "255.255.255.252"
                }
            ]
        }
    ]

    with open("interconnects.yml", mode="a") as f:
        yaml.dump(stuff, f, default_flow_style=False)
    print(stuff)


# Stuff coming from NSO
site_slug = "cst"
role_slug = "access-interconnects"

a_device = "PE01-XR9KV"
a_interface = "GigabitEthernet0/0/0/1"
z_device = "PA01-CSR1KV"
z_interface = "GigabitEthernet2"

write_yaml(
    site_slug=site_slug,
    role_slug=role_slug,
    a_device=a_device,
    z_device=z_device,
    a_interface=a_interface,
    z_interface=z_interface
)
