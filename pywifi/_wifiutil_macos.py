#!/usr/bin/env python3
# vim: set fileencoding=utf-8

"""Implementations of wifi functions of macOS."""

import logging
import objc

from .const import *
from .profile import Profile


CWSecurityNone = 0
CWSecurityWPA = 7
CWSecurityWPA2 = 9
CWSecurityWPAPSK = 2
CWSecurityWPA2PSK = 4

kCWInterfaceStateInactive = 0
kCWInterfaceStateScanning = 1
kCWInterfaceStateAuthenticating = 2
kCWInterfaceStateAssociating = 3
kCWInterfaceStateRunning = 4

status_dict = {
    kCWInterfaceStateRunning: IFACE_CONNECTED,
    kCWInterfaceStateInactive: IFACE_INACTIVE,
    kCWInterfaceStateAuthenticating: IFACE_CONNECTING,
    kCWInterfaceStateAssociating: IFACE_CONNECTING,
    kCWInterfaceStateScanning: IFACE_SCANNING,
}

objc.loadBundle('CoreWLAN', bundle_path = '/System/Library/Frameworks/CoreWLAN.framework', module_globals = globals())

class WifiUtil():
    """WifiUtil implements the wifi functions in macOS."""

    _connections = {}
    _logger = logging.getLogger('pywifi')

    def scan(self, obj):
        """Trigger the wifi interface to scan."""

        iface = self._get_interface(obj['name'])
        iface.scanForNetworksWithName_error_(None, None)

    def scan_results(self, obj):
        """Get the AP list after scanning."""

        iface = self._get_interface(obj['name'])
        raw_networks = iface.cachedScanResults()
        bsses = []

        for raw_network in raw_networks:
            bss = Profile()
            bss.bssid = raw_network.bssid()
            bss.freq = raw_network.wlanChannel().channelNumber()
            bss.signal = raw_network.rssiValue()
            
            # Fix SSID handling - ensure proper string conversion
            ssid_obj = raw_network.ssid()
            if ssid_obj:
                # Convert NSString to Python string
                bss.ssid = str(ssid_obj)
            else:
                bss.ssid = ''
            
            bss.akm = []

            # Check security type and set corresponding AKM type
            if raw_network.supportsSecurity_(CWSecurityNone):
                bss.akm.append(AKM_TYPE_NONE)
            if raw_network.supportsSecurity_(CWSecurityWPAPSK):
                bss.akm.append(AKM_TYPE_WPAPSK)
            if raw_network.supportsSecurity_(CWSecurityWPA2PSK):
                bss.akm.append(AKM_TYPE_WPA2PSK)
            if raw_network.supportsSecurity_(CWSecurityWPA):
                bss.akm.append(AKM_TYPE_WPA)
            if raw_network.supportsSecurity_(CWSecurityWPA2):
                bss.akm.append(AKM_TYPE_WPA2)

            # If no security type detected, set to NONE
            if not bss.akm:
                bss.akm.append(AKM_TYPE_NONE)

            bss.auth = [AUTH_ALG_OPEN]  # Fix: should be list format to match Windows version

            bsses.append(bss)

        self._logger.debug("Scan found %d networks.", len(bsses))
        return bsses

    def connect(self, obj, network):
        """Connect to the specified AP."""

        iface = self._get_interface(obj['name'])
        raw_networks = iface.cachedScanResults()

        for raw_network in raw_networks:
            if raw_network.ssid() == network.ssid:
                result = iface.associateToNetwork_password_error_(raw_network, network.key, None)
                self._logger.debug('connect result: %s', result)
                break

    def disconnect(self, obj):
        """Disconnect to the specified AP."""

        iface = self._get_interface(obj['name'])
        iface.disassociate()

    def add_network_profile(self, obj, params):
        """Add an AP profile for connecting to afterward."""

        iface = self._get_interface(obj['name'])
        configuration = iface.configuration()
        orig_profiles = configuration.networkProfiles()
        orig_mutable_profiles = NSMutableOrderedSet.alloc().initWithOrderedSet_(orig_profiles)
        
        # Process AKM type
        params.process_akm()
        
        ssid_bytes = str.encode(params.ssid)
        profile = CWMutableNetworkProfile.alloc().init()
        profile.setSsidData_(ssid_bytes)
        
        # Set security mode based on AKM type
        if params.akm and params.akm[-1] != AKM_TYPE_NONE:
            if params.akm[-1] == AKM_TYPE_WPAPSK:
                profile.setSecurity_(CWSecurityWPAPSK)
            elif params.akm[-1] == AKM_TYPE_WPA2PSK:
                profile.setSecurity_(CWSecurityWPA2PSK)
            elif params.akm[-1] == AKM_TYPE_WPA:
                profile.setSecurity_(CWSecurityWPA)
            elif params.akm[-1] == AKM_TYPE_WPA2:
                profile.setSecurity_(CWSecurityWPA2)
            else:
                profile.setSecurity_(CWSecurityNone)
        else:
            profile.setSecurity_(CWSecurityNone)
        
        orig_mutable_profiles.addObject_(profile)
        configuration.setNetworkProfiles_(orig_mutable_profiles)
        result = iface.commitConfiguration_authorization_error_(configuration, None, None)
        
        if not result:
            self._logger.debug("Add profile failed")
        
        return params

    def network_profile_name_list(self, obj):
        """Get AP profile names."""
        
        iface = self._get_interface(obj['name'])
        raw_networks = iface.configuration().networkProfiles()
        
        profile_name_list = []
        for i in range(0, raw_networks.count()):
            profile_name = raw_networks.objectAtIndex_(i).ssid()
            if profile_name:
                profile_name_list.append(profile_name)
        
        return profile_name_list

    def network_profiles(self, obj):
        """Get AP profiles."""

        iface = self._get_interface(obj['name'])
        raw_networks = iface.configuration().networkProfiles()

        bsses = []

        for i in range(0, raw_networks.count()):
            bss = Profile()
            bss.ssid = raw_networks.objectAtIndex_(i).ssid()
            bss.akm = []

            security_type = raw_networks.objectAtIndex_(i).security()
            if security_type == CWSecurityWPAPSK:
                bss.akm.append(AKM_TYPE_WPAPSK)
            elif security_type == CWSecurityWPA2PSK:
                bss.akm.append(AKM_TYPE_WPA2PSK)
            elif security_type == CWSecurityWPA:
                bss.akm.append(AKM_TYPE_WPA)
            elif security_type == CWSecurityWPA2:
                bss.akm.append(AKM_TYPE_WPA2)
            else:
                bss.akm.append(AKM_TYPE_NONE)

            bss.auth = [AUTH_ALG_OPEN]  # Fix: should be list format

            bsses.append(bss)

        return bsses

    def remove_all_network_profiles(self, obj):
        """Remove all the AP profiles."""

        profile_name_list = self.network_profile_name_list(obj)
        
        for profile_name in profile_name_list:
            self._logger.debug("delete profile: %s", profile_name)
        
        iface = self._get_interface(obj['name'])
        configuration_copy = iface.configuration()
        configuration_copy.setNetworkProfiles_(None)
        result = iface.commitConfiguration_authorization_error_(configuration_copy, None, None)
        
        if not result:
            self._logger.debug("Remove all profiles failed")

    def status(self, obj):
        """Get the wifi interface status."""

        iface = self._get_interface(obj['name'])
        interface_state = iface.interfaceState()
        return status_dict.get(interface_state, IFACE_INACTIVE)

    def interfaces(self):
        """Get the wifi interface lists."""
        
        ifaces = []
        interface_names = CWWiFiClient.interfaceNames()
        
        if interface_names:
            for f in interface_names:
                iface = {}
                iface['name'] = f
                ifaces.append(iface)
        else:
            self._logger.error("No wifi interfaces found!")

        return ifaces

    def _get_interface(self, iface_name):
        """Get the CoreWLAN interface object."""
        
        return CWInterface.interface()
