```yaml
gminfo37_specifications:
  device: gminfo37
  platform: full_gminfo37_gb_broxton
  manufacturer: Harman_Samsung
  android: 12_API_32_Sv2_W231E-Y177.6.1-SIHM22B-499.2_2025-04-03
  security_patch: 2025-02-05
  vehicles: Chevrolet_GMC_Cadillac_2023_onward
  build_date: 2025-03-05_01:42:54_EST
  build_type: user_release_keys
  build_fingerprint: gm/full_gminfo37_gb/gminfo37:12/W231E-Y177.6.1-SIHM22B-499.2/231:user/release-keys
  kernel: 4.19.305_240125T145315Z_00094_Mar_5_2025

cpu:
  model: Intel_Atom_x7_A3960
  part: LH8066803226000
  arch: Goldmont_14nm_Apollo_Lake_Broxton
  qualified: AEC_Q100_automotive
  socket: BGA1296_soldered
  cores: 4
  threads: 4
  freq_base: 800
  freq_boost: 2400
  cache_l2: 2
  tdp: 10
  current_freq: 300
  operating_temp: 53C

gpu:
  model: Intel_HD_Graphics_505
  pci_id: 0000:00:02.0
  arch: Gen_9_Apollo_Lake_14nm
  eus: 18
  freq_base: 300
  freq_boost: 750
  freq_current: 300
  memory: shared_system_ddr
  decode_h264: true
  decode_hevc_8bit: true
  decode_hevc_10bit: true
  decode_vp9: true
  decode_av1: true
  decode_vc1: true
  max_displays: 3
  interfaces: [DP, eDP, HDMI_1.4]
  opengl_es: 3.2
  vulkan: 1.1.128   # Y177 snapshot value; Y181 live (Jun-2026) reports API version Vulkan 1.1.0 (raw 4198400 = 0x401000). 1.1.128 is likely a driver/conformance build, not the API version. Vulkan unused at runtime (GLES 3.2 backend).
  directx: 12.1
  secure_playback: true

memory:
  physical_capacity: 8192    # 8 GB LPDDR4 (4x Micron MT53E512M32D2DS-053), teardown-verified
  total: 6144                # guest allocation visible to Android (~5.66 GB kernel-visible)
  available: 3584
  utilization: 56
  committed_oversubscription: 88800
  ram_model: LPDDR4_shared
  swap: 0

storage:
  total: 65536
  available: 40960
  data_partition: 39936
  data_used: 4300
  data_available: 35636
  system_partition: 2969
  system_used: 2785
  system_available: 184
  vendor_partition: 438
  vendor_used: 428
  vendor_available: 1
  product_partition: 2458
  product_used: 2274
  product_available: 184
  utilization_warning: vendor_100_percent_full

display:
  panel_model: DD134IA_01B
  manufacturer: Chimei_Innolux_CMN
  product_id: 41268
  manufacture_date: week_36_2020
  width: 2400
  height: 960
  fps: 60.001434
  size_mm: [316, 126]
  diagonal: 13.39
  dpi_actual: [192.911, 193.523]
  dpi_logical: 200
  orientation: landscape_0
  rotation: 0
  mode_id: 1
  color_depth: 8bit
  color_modes: [0_native]
  hdr_support: false
  brightness_range: [0.0, 1.0]
  brightness_default: 0.39763778
  brightness_current: 0.3976378
  touch_dimensions: [2400, 960]
  vsync_offset: 2500000ns
  presentation_deadline: 14666268ns

input:
  touchscreen:
    model: Atmel_maXTouch
    bus: i2c_7_004b
    device_id: event1
    resolution: [2400, 960]
    multitouch: 16_points
    pressure_range: [0, 255]
    gestures: true
    palm_rejection: true
  faceplate:
    model: Faceplate_Controller
    bus: i2c_7_0012
    device_id: event2
    type: hardware_buttons
    keylayout: /system/usr/keylayout/Faceplate_Controller.kl

audio:
  codec: Harman_custom_DSP
  service: vendor.hardware.audio@5.0_harman_custom_service
  sample_rates: [8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 96000]
  channels_max: 8
  effects: [AEC, NS, AGC, preprocessing]
  buses: 8_virtual_buses
  latency_target: 50ms
  output_devices: [speaker, bluetooth, usb, line_out]
  input_devices: [microphone, bluetooth, line_in]

video_hardware_decoders:
  h264:
    codec: OMX.Intel.hw_vd.h264
    hw_accelerated: true
    max_resolution: 3840x2160
    max_fps: 60
    profiles: [Baseline_5.1, Main_5.1, High_5.1, ConstrainedHigh_5.1]
    measured_1280x720: 460_590_fps
    measured_1920x1088: 320_360_fps
    secure_playback: true
  hevc:
    codec: OMX.Intel.hw_vd.h265
    hw_accelerated: true
    max_resolution: 3840x2160
    max_fps: 60
    profiles: [Main_5.1, Main10_5.1]
    measured_1280x720: 250_500_fps
    measured_1920x1080: 190_400_fps
    measured_3840x2160: 120_130_fps
    secure_playback: true
  vp8:
    codec: OMX.Intel.hw_vd.vp8
    hw_accelerated: true
    max_resolution: 3840x2160
    max_fps: 60
    measured_1280x720: 200_400_fps
    measured_1920x1080: 150_330_fps
  vp9:
    codec: OMX.Intel.hw_vd.vp9
    hw_accelerated: true
    max_resolution: 3840x2160
    max_fps: 60
    profiles: [Profile_0_5.2, Profile_2_5.2, Profile_2HDR_5.2]
    measured_1280x720: 400_600_fps
    measured_1920x1080: 350_420_fps
    measured_3840x2160: 100_130_fps
  av1:
    codec: c2.android.av1.decoder
    hw_accelerated: false
    software_only: true
    max_resolution: 2048x2048
    profiles: [Main8_5.3, Main10HDR10_5.3, Main10HDRPlus_5.3]

network:
  ethernet:
    interface: eth0
    driver: Intel_I211
    mac: 02:04:00:00:01:00
    speed: 1000mbps
    vlans: [vlan4_172.16.4.100, vlan5_192.168.1.100]
  wifi:
    chipset: Broadcom_BCM
    driver: dhd
    mac: F8:6D:CC:DC:32:D4
    bands: [2.4GHz, 5GHz]
    standards: [802.11a, 802.11b, 802.11g, 802.11n, 802.11ac]
    hotspot: supported
    current_ssid: ZSmart
    current_rssi: -39dBm
    current_ip: 192.168.4.65
  bluetooth:
    version: 5.0
    mac: F8:6D:CC:DC:32:D6
    profiles: [HFP, A2DP, AVRCP, PBAP, MAP, HID]
    name: myChevrolet
    paired_devices: [iPhone_64:31:35:8C:29:69]
    active_hfp: true

usb:
  controller: xHCI_Intel
  ports: multiple
  otg: false
  host_mode: true
  adb_enabled: true
  aptiv_bridges: 2x_H2H_VID_10646_PID_261
  aptiv_pd_hubs: 2x_GM_V10_E2_VID_10646_PID_306
  aptiv_dfu: 2x_Vendor_DFU_VID_10646_PID_288
  mcp2200_serial: debug_interface_VID_1240_PID_223

thermal:
  tdp: 10
  cooling: passive
  automotive_qualified: true
  extended_temp_range: true
  cpu_temp: 53C
  gpu_temp: 53C
  skin_temp: 25C
  battery_temp: 25C
  thermal_throttling: none

power:
  source: vehicle_12v_direct
  battery: none
  state: always_on
  management: automotive_grade
  suspend: disabled

carlink_optimization:
  hardware_sufficient: true
  adapter_bottleneck: false
  primary_target: mediacodec_config
  secondary_target: thread_scheduling
  tertiary_target: usb_permissions
  target_resolution: 2400x960_60
  audio_latency_target: 50ms
  stability: automotive_grade
  codec_preference: OMX.Intel.hw_vd.h264
  buffer_config: adaptive_playback_disabled
  performance_mode: quality_over_speed

performance_analysis:
  cpu_adequate: true
  gpu_adequate: true
  memory_adequate: true
  decode_capability: exceeds_requirements
  bottleneck_location: software_optimization
  uptime_stability: 4.8_days
  boot_count: 254
  selinux: permissive
  verified_boot: green_locked

system_services:
  gm_specific:
    - GMLoggerService
    - ClusterService
    - CarPlayService
    - GALService
    - TCPS_privacy_service
    - GMAnalytics
    - TrustedDevice_phone_key
    - SubscriptionManager
    - OnStarServices_integrated
  google_services:
    - GooglePlayServices_fragmented_1.3GB_ram
    - GoogleMaps_preinstalled
    - AutoTemplateHost
  media_sessions:
    - TunerService_active
    - BluetoothMediaBrowser
    - LocalMediaPlayer_usb

android_automotive:
  car_service: active
  vhal_properties: 156_registered
  occupant_zones: driver_only
  ux_restrictions: driving_state_monitoring
  power_policy: system_power_policy_all_on
  audio_zones: 8_virtual_buses
  projection_support: [AndroidAuto, CarPlay]
```