# Loxberry Plugin Link2Home

This repository contains a plugin for the Loxberry to enable remote control of Link2Home sockets via UDP,
allowing users to switch specified relays on or off based on command-line inputs.

The plugin read configuration details from an INI file and send a hex-encoded UDP command to the specified
IP and port for an specified mac address.

The scripts only trigger the link2home garden socket outlet (WiFi version).

## Requirements

### Perl

    - Perl 5.x
    - IO::Socket::INET module (typically included with Perl)
    - Socket module (typically included with Perl)

## Configuration File Setup

Before running any script, ensure you have the `config.ini` file setup right. You can do this over the Loxberry Webinterface.
Setup the broadcast ip of your network segment where the link2home garden scoket outlet (WiFi version) is installed.
The port should be `35932`. Every devie has their own MAC_ADDRESS (check this over your networks manager), example are 3 socket outlets
in this example `config.ini` file.

    [General]
    BROADCAST_IP = 192.168.1.255
    PORT = 35932
    [Device1]
    MAC_ADDRESS = 98D86310AAAA
    [Device2]
    MAC_ADDRESS = 98D86310ABBB
    [Device3]
    MAC_ADDRESS = 98D86310ACCC

## Installation

Installation over the Loxberry Webinterface in the plugin section. Check my [GitHub Loxberry Plugin Link2Home](https://github.com/omerbeg/loxberry-plugin-link2home) site
for the latest release.

## Contributing

Contributions to these scripts are welcome, especially in areas such as error handling, logging, and extending functionality. Please submit a pull request or raise an issue if you have suggestions or improvements.

## License

This script is released under the GNU GENERAL PUBLIC LICENSE. See `LICENSE` file for more details.
