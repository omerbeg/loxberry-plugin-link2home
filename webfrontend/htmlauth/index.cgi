#!/usr/bin/perl

# Copyright 2024 Begzudin Omerovic, begzudin.omerovic@oglasi.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

use strict;
use warnings;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use Data::Dumper;
use CGI;


use IO::Socket::INET;
use Socket;
use HTML::Template;

##########################################################################
# Variables
##########################################################################

# Create a new CGI object
my $cgi = CGI->new;
$cgi->import_names('R');
my $q = $cgi->Vars;

# Version of this script
my $version = LoxBerry::System::pluginversion();

# Path to config.ini file and template file
my $cfg = $lbpconfigdir . "/config.ini";

# Read current config values
my %config = read_config($cfg);

# Create a logging object
#my $log = LoxBerry::Log->new ( name => 'link2home' );
# Create a logging object
my $log = LoxBerry::Log->new ( 
        name => 'link2home', 
        package => 'Update',  
        loglevel => 7,
        filename => "$lbslogdir/link2home.log",
        append => 1,
);

# We start the log. It will print and store some metadata like time, version numbers, and the string as log title 
LOGSTART "Link2Home started";
  
#########################################################################
# Parameter
#########################################################################

my $error;

# Init Template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/link2home.tmpl", 
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

 # Language Phrases
my %L = LoxBerry::Web::readlanguage($template, "language.ini");

# Print the form
&form_print();

exit;

##########################################################################
# Print Form
##########################################################################

sub form_print
{
	
    
    # Navbar
    our %navbar;
	$navbar{1}{Name} = "$L{'SETTINGS.LABEL_GENERAL_SETTINGS'}";
	$navbar{1}{URL} = 'index.cgi?form=1';

    $navbar{2}{Name} = "$L{'SETTINGS.LABEL_DEVICE_MANAGEMENT'}";
    $navbar{2}{URL} = 'index.cgi?form=2';

    $navbar{3}{Name} = "$L{'SETTINGS.LABEL_RELAY_CONTROL'}";
    $navbar{3}{URL} = 'index.cgi?form=3';
    
    # Set header for our side
    my $version = LoxBerry::System::pluginversion();

    # Populate the device dropdown in the form
    &device_loop();

    # If a device is selected, populate the form with the device's current config (MAC Address)
    
    if (my $selected_device = $cgi->param('device')) {
        $template->param(MAC_ADDRESS => $config{$selected_device}{'MAC_ADDRESS'});
        $template->param(DEVICE_NAME => $selected_device);
    } else {
        # Default values if no device is selected yet
        $template->param(MAC_ADDRESS => '');
    }
    
if ($R::form eq '3' || $R::saveformdata3) {
  $R::form = 3;
  $navbar{3}{active} = 1;
  $template->param( "FORM3", 1);
    # Handle relay control form submission
    if ($cgi->param('relay') && $cgi->param('state') && $cgi->param('device')) {
        my $relay = $cgi->param('relay');
        my $state = $cgi->param('state');
        my $selected_device = $cgi->param('device');

        my $COMMAND_PREFIX = "a104";
        my %COMMAND_SUFFIX = (
            1 => "000901f202d171500101",
            2 => "000901f202d171500102"
        );
        my %STATE_CODES = (
            'on'  => 'FF',
            'off' => '00'
        );

        if (exists $COMMAND_SUFFIX{$relay} && exists $STATE_CODES{$state}) {
            my $sock = IO::Socket::INET->new(
                Proto => 'udp',
                Broadcast => 1,
                LocalPort => 0
            ) or die "Could not create socket: $!\n";

            # Prepare the command using the MAC address of the selected device
            my $command = $COMMAND_PREFIX . $config{$selected_device}{'MAC_ADDRESS'} . $COMMAND_SUFFIX{$relay} . $STATE_CODES{$state};
            my $message = pack("H*", $command);

            # Use the global BROADCAST_IP and PORT
            my $iaddr = inet_aton($config{'General'}{'BROADCAST_IP'}) or die "Invalid IP address: $config{'General'}{'BROADCAST_IP'}\n";
            my $sockaddr = sockaddr_in($config{'General'}{'PORT'}, $iaddr);

            $sock->send($message, 0, $sockaddr) or die "Send error: $!\n";
            $sock->close();

            $template->param(MESSAGE => "Command sent to relay $relay of $selected_device: " . ($state eq 'on' ? 'ON' : 'OFF'));
        } else {
            $template->param(MESSAGE => "Error: Invalid relay or state parameters.");
        }

        $template->param("RELAY_${relay}_SELECTED" => 1);
        $template->param("STATE_" . uc($state) . "_SELECTED" => 1);
    }

} elsif ($R::form eq '2' || $R::saveformdata2) {
    $R::form = 2;
    $navbar{2}{active} = 1;
    $template->param("FORM2",1);

    # Handle form submission to add a new device
    if ($cgi->param('add_device')) {
        my $new_device_name = $cgi->param('new_device_name');
        my $new_mac_address = $cgi->param('new_mac_address');

        if ($new_device_name && $new_mac_address) {
            # Check if the device already exists
            if (exists $config{$new_device_name}) {
                $template->param(MESSAGE => "Error: Device $new_device_name already exists!");
            } else {
                # Add the new device to the config
                $config{$new_device_name}{'MAC_ADDRESS'} = $new_mac_address;

                # Save the updated configuration
                write_config($cfg, \%config);

                $template->param(MESSAGE => "New device $new_device_name added successfully!");
                &device_loop();              
            }
        } else {
            $template->param(MESSAGE => "Error: Device name and MAC address are required!");
        }
    }

    # Handle device deletion
    if ($cgi->param('delete_device')) {
        my $device_to_delete = $cgi->param('device');

        if ($device_to_delete && exists $config{$device_to_delete}) {
            # Remove the device from the config
            delete $config{$device_to_delete};

            # Save the updated configuration
            write_config($cfg, \%config);

            $template->param(MESSAGE => "Device $device_to_delete has been deleted successfully!");
            $template->param(MAC_ADDRESS => '');

            &device_loop();
    
        } else {
            $template->param(MESSAGE => "Error: Device $device_to_delete does not exist!");
        }
    }

    # Handle form submission to save new config (updates or adds devices)
    if ($cgi->param('save_device')) {
        my $selected_device = $cgi->param('device');
        my $mac_address = $cgi->param('mac_address');

        if ($selected_device && $mac_address) {
            # Add or update the device configuration
            $config{$selected_device}{'MAC_ADDRESS'} = $mac_address;

            # Save the new configuration values to config.ini
            write_config($cfg, \%config);

            $template->param(MESSAGE => "Configuration for $selected_device saved successfully!");
            $template->param(MAC_ADDRESS => $config{$selected_device}{'MAC_ADDRESS'});
            
        } else {
            # Handle missing fields (device or mac_address not set)
            $template->param(MESSAGE => "Error: All fields are required!");
        }
    }

} elsif ($R::form eq '1' || $R::saveformdata1 || !$R::form) {
    $R::form = 1;
    $navbar{1}{active} = 1;
    $template->param("FORM1",1);
    my $broadcast_ip = $config{'General'}{'BROADCAST_IP'};
    my $port         = $config{'General'}{'PORT'};
    
    my $new_broadcast_ip = $cgi->param('broadcast_ip');
    my $new_port         = $cgi->param('port');

    $template->param(BROADCAST_IP => $broadcast_ip);
    $template->param(PORT => $port);
    

    if ($cgi->param('save_general')) {
        if ($new_broadcast_ip && $new_port) {
            $config{'General'}{'BROADCAST_IP'}=$new_broadcast_ip;
            $config{'General'}{'PORT'}=$port;
            # Save the updated configuration
            write_config($cfg, \%config);
            
            $template->param(BROADCAST_IP => $new_broadcast_ip);
            $template->param(PORT => $new_port);
            $template->param(MESSAGE => "New general settings saved successfully!");
                    
        }  else {
            $template->param(MESSAGE => "Error: Broacast IP and Port are required!");
        }
    }

} elsif (!$R::form ) {
    $R::form = '1'; 
}

# Template Vars and Form parts
$template->param( "LBPPLUGINDIR", $lbpplugindir);

# Template
LoxBerry::Web::lbheader($L{'COMMON.LABEL_PLUGINTITLE'} . " V$version", "https://wiki.loxberry.de/plugins/link2home/", "help.html");
print $template->output();
LoxBerry::Web::lbfooter();
exit;

}

sub device_loop() {

    my @device_loop;
    # Read current config values
    foreach my $device (grep { $_ ne 'General' } keys %config) {
        push @device_loop, {
        DEVICE_NAME => $device,
        DEVICE_SELECTED => ($cgi->param('device') && $cgi->param('device') eq $device) ? 'selected' : ''
           };
        }
    $template->param(DEVICES => \@device_loop);

}
sub error
{
	$template->param( "ERROR", 1);
	$template->param( "ERRORMESSAGE", $error);
	LoxBerry::Web::lbheader($L{'COMMON.LABEL_PLUGINTITLE'} . " V$version", "https://wiki.loxberry.de/plugins/link2home/", "help.html");
	print $template->output();
	LoxBerry::Web::lbfooter();

	exit;
}
# Read configuration
sub read_config {
    my ($filename) = @_;
    open my $fh, '<', $filename or die "Cannot open configuration file: $!";
    my %config;
    my $current_section;
    while (my $line = <$fh>) {
        chomp $line;
        $line =~ s/^\s+|\s+$//g; # Trim spaces
        next if $line eq "" || $line =~ /^#/; # Skip empty lines and comments
        if ($line =~ /^\[(.*)\]$/) {
            $current_section = $1;
            next;
        }
        if ($line =~ /^(.*?)\s*=\s*(.*)$/) {
            $config{$current_section}{$1} = $2;
        }
    }
    close $fh;
    return %config;
}

# Write configuration (used when updating/adding devices)
sub write_config {
    my ($filename, $config) = @_;
    open my $fh, '>', $filename or die "Cannot open configuration file: $!";
    print $fh "[General]\n";
    print $fh "BROADCAST_IP = $config->{'General'}{'BROADCAST_IP'}\n";
    print $fh "PORT = $config->{'General'}{'PORT'}\n";
    for my $device (keys %$config) {
        next if $device eq 'General'; # Skip the General section
        print $fh "[$device]\n";
        print $fh "MAC_ADDRESS = $config->{$device}{'MAC_ADDRESS'}\n";
    }
    close $fh;
}


