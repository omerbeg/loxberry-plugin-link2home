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
use Config::Simple;
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
#my %config = read_config($cfg);
my $config;

$config = new Config::Simple($cfg) or die $config->error();

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

    # Populate the device dropdown in the form
    &device_loop();

    # If a device is selected, populate the form with the device's current config (MAC Address)
    
    if (my $selected_device = $cgi->param('device')) {
        my $value=$selected_device.".MAC_ADDRESS";
        $template->param(MAC_ADDRESS => $config->param($value));
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
            my $value=$selected_device.".MAC_ADDRESS";
            my $command = $COMMAND_PREFIX . $config->param($value) . $COMMAND_SUFFIX{$relay} . $STATE_CODES{$state};
            my $message = pack("H*", $command);

            # Use the global BROADCAST_IP and PORT
            my $iaddr = inet_aton($config->param("General.BROADCAST_IP")) or die "Invalid IP address: " . $config->param("General.BROADCAST_IP") ."\n";
            my $sockaddr = sockaddr_in($config->param("General.PORT"), $iaddr);

            $sock->send($message, 0, $sockaddr) or die "Send error: $!\n";
            $sock->close();

            my $message = "$L{'SETTINGS.LABEL_COMMAND_SENT'}" . " " . $relay . " $L{'SETTINGS.LABEL_OF'}". " $selected_device: " . ($state eq 'on' ? "$L{'SETTINGS.LABEL_ON'}" : "$L{'SETTINGS.LABEL_OFF'}");
            $template->param(MESSAGE => $message);

        } else {
            my $message =  "$L{'SETTINGS.LABEL_ERROR_INVALID_RELAY_PARAM'}";
            $template->param(MESSAGE => $message);
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
            if ($config->param("$new_device_name")) {
                my $message= "$L{'SETTINGS.LABEL_ERROR_DEVICE'}". " " . $new_device_name. " " . "$L{'SETTINGS.LABEL_ALREADY_EXISTS'}";
                $template->param(MESSAGE => $message);
            } else {
                # Add the new device to the config
                my $value=$new_device_name.".MAC_ADDRESS";
                $config->param($value, $new_mac_address);

                # Save the updated configuration
                $config->save;

                my $message= "$L{'SETTINGS.LABEL_NEW_DEVICE'}" . " ". $new_device_name . " " . "$L{'SETTINGS.LABEL_ADDED_SUCCESSFULLY'}";

                $template->param(MESSAGE => $message);
                &device_loop();              
            }
        } else {
            my $message= "$L{'SETTINGS.LABEL_ERROR_NAME_MAC_REQUIERED'}";
            $template->param(MESSAGE => $message);
        }
    }

    # Handle device deletion
    if ($cgi->param('delete_device')) {
        my $device_to_delete = $cgi->param('device');
        my $value=$device_to_delete.".MAC_ADDRESS";
            
        if ($device_to_delete && $config->param($value)) {
            # Remove the device from the config
            delete_block($device_to_delete);

            # Save the updated configuration
            $config->save;

            my $message="$L{'SETTINGS.LABEL_DEVICE'}". " ".$device_to_delete . " ". "$L{'SETTINGS.LABEL_DELETED_SUCCESSFULLY'}";;
            $template->param(MESSAGE => $message);
            $template->param(MAC_ADDRESS => '');

            &device_loop();
    
        } else {
            my $message="$L{'SETTINGS.LABEL_ERROR_DEVICE_NAME'}". " " . $device_to_delete. " " . "$L{'SETTINGS.LABEL_DOESNOT_EXISTS'}";
            $template->param(MESSAGE => $message);
        }
    }

    # Handle form submission to save new config (updates or adds devices)
    if ($cgi->param('save_device')) {
        my $selected_device = $cgi->param('device');
        my $mac_address = $cgi->param('mac_address');

        if ($selected_device && $mac_address) {
            # Add or update the device configuration
            #$config{$selected_device}{'MAC_ADDRESS'} = $mac_address;
            my $value=$selected_device.".MAC_ADDRESS";
            $config->param($value, $mac_address);

            # Save the new configuration values to config.ini
            #write_config($cfg, \%config);
            $config->save;

            my $message = "$L{'SETTINGS.LABEL_CONFIGURATION_FOR'}". " " . $selected_device. " "."$L{'SETTINGS.LABEL_SAVED_SUCCESSFULLY'}";

            $template->param(MESSAGE => $message);
            $template->param(MAC_ADDRESS => $config->param($value));
            
        } else {
            # Handle missing fields (device or mac_address not set)
            my $message="$L{'SETTINGS.LABEL_ERROR_ALL_FIELD_REQUIRED'}";
            $template->param(MESSAGE => $message);
        }
    }

} elsif ($R::form eq '1' || $R::saveformdata1 || !$R::form) {
    $R::form = 1;
    $navbar{1}{active} = 1;
    $template->param("FORM1",1);
    my $broadcast_ip = $config->param("General.BROADCAST_IP");
    my $port         = $config->param("General.PORT");
    
    my $new_broadcast_ip = $cgi->param('broadcast_ip');
    my $new_port         = $cgi->param('port');

    $template->param(BROADCAST_IP => $broadcast_ip);
    $template->param(PORT => $port);
    

    if ($cgi->param('save_general')) {
        if ($new_broadcast_ip && $new_port) {
            $config->param("General.BROADCAST_IP",$new_broadcast_ip);
            $config->param("General.PORT",$port);
            # Save the updated configuration
            #write_config($cfg, \%config);
            $config->save;

            $template->param(BROADCAST_IP => $new_broadcast_ip);
            $template->param(PORT => $new_port);
            my $message = "$L{'SETTINGS.LABEL_GENERAL_SETTINGS_SAVED'}";
            $template->param(MESSAGE => $message);
                    
        }  else {
            my $message="$L{'SETTINGS.ERROR_BROADCAST_PORT_REQUIERED'}";
            $template->param(MESSAGE => $message);
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

# Refactored device_loop function using Config::Simple
sub device_loop() {
    
    # Create an array to store device details
    my @device_loop;

    # Iterate over sections, ignoring 'General'

    foreach my $device ($config->param()) {
               
        next if $device =~ /General/; # Skip the General section
        
        # Split the device string on the dot and take the first part
        my ($device_name) = split(/\./, $device);
        
        push @device_loop, {
            DEVICE_NAME     => $device_name,
            DEVICE_SELECTED => ($cgi->param('device') && $cgi->param('device') eq $device_name) ? 'selected' : ''
        };
    }

    # Set the template parameters with the devices array
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

# Function to delete a block (section) from the configuration file
sub delete_block {
    my ($block_to_delete) = @_;

     # Iterate over all keys in the configuration
    foreach my $key ($config->param()) {
        # If the key belongs to the block we want to delete
        if ($key =~ /^$block_to_delete\./) {
            # Delete the key from the config
            $config->delete($key);
        }
    }

    # Write the updated configuration back to the file
    $config->write() or die $config->error();
}