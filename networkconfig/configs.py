import os
import getpass
import ipaddress
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def main():
    ip_address = input("Add meg a konfigurálandó eszköz SSH IP címét: ").strip()
    hostname = input("Kérem a rátöltendő konfiguráció hosztnevét (pl. KR1): ").strip()
    
    address_table_path = "configs/addresstable.conf"
    config_file_path = f"configs/{hostname}.conf"

    if not os.path.isfile(config_file_path):
        print(f"Hiba: A konfigurációs fájl nem található: {config_file_path}")
        return
        
    if not os.path.isfile(address_table_path):
        print(f"Hiba: A címzési tábla nem található: {address_table_path}")
        return

    username = input("SSH Felhasználónév: ").strip()
    password = getpass.getpass("SSH Jelszó (a karakterek nem látszanak): ")

    device = {
        'device_type': 'cisco_ios',
        'host': ip_address,
        'username': username,
        'password': password,
    }

    try:
        print(f"\nCsatlakozás a(z) {ip_address} címhez...")
        with ConnectHandler(**device) as net_connect:
            
            print(f"[{hostname}] Alap konfiguráció küldése a(z) {config_file_path} fájlból...")
            output1 = net_connect.send_config_from_file(config_file_path)
            
            interface_cmds = []
            with open(address_table_path, 'r') as f:
                for line in f:
                    parts = line.split()
                    
                    if len(parts) == 3 and parts[0] == hostname:
                        intf, ip_data = parts[1], parts[2]
                        interface_cmds.append(f"interface {intf}")
                        
                        if '.' in intf and not intf.lower().startswith('vlan'):
                            vlan_id = intf.split('.')[1]
                            interface_cmds.append(f" encapsulation dot1Q {vlan_id}")
                            
                        if ip_data.upper() == "DHCP":
                            interface_cmds.append(" ip address dhcp")
                        else:
                            if '/' not in ip_data:
                                ip_data += '/24'
                            net = ipaddress.IPv4Interface(ip_data)
                            interface_cmds.append(f" ip address {net.ip} {net.netmask}")
                            
                        interface_cmds.append(" no shutdown")
                        interface_cmds.append(" exit")

            output2 = ""
            if interface_cmds:
                print(f"[{hostname}] Interfész IP címek beállítása...")
                output2 = net_connect.send_config_set(interface_cmds)
            else:
                print(f"[{hostname}] Figyelmeztetés: Nem találtam a hosztnévhez tartozó IP címeket a címzési táblában.")

            print("\n--- Kiment az alap konfiguráció és az IP címek is! ---")
            print("--- Alap konfig kimenet ---")
            print(output1)
            if output2:
                print("--- Interfész konfig kimenet ---")
                print(output2)
            print("--------------------------------------------------")

    except NetmikoAuthenticationException:
        print("\nKritikus Hiba: Sikertelen hitelesítés! Rossz felhasználónév vagy jelszó.")
    except NetmikoTimeoutException:
        print("\nKritikus Hiba: Időtúllépés! Az eszköz nem válaszol vagy a tűzfal blokkol.")
    except Exception as e:
        print(f"\nVáratlan hiba történt: {e}")

if __name__ == "__main__":
    main()