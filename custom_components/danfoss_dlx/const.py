"""Constants for the Danfoss DLX integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN = "danfoss_dlx"

DEFAULT_SCAN_INTERVAL = 30  # seconds

CONF_HISTORY_CUTOFF = "history_cutoff"
CONF_IMPORT_VERSION = "import_version"
SERVICE_IMPORT_HISTORY = "import_history"

# Bumped whenever a fix changes what the history import produces, so existing
# installations re-import instead of keeping data from a buggy earlier run.
IMPORT_VERSION = 2

# The inverter's built-in "Theia" web server exposes data points as
# eNEXUS_xxxx[s:<system>,t:<systemType>] paths, read in a single batched
# JSON-RPC call to /rpc/GeteNexusData. system/systemType identify which
# inverter to query and are discovered at setup time from file/systemList.json.
STATUS_MAP = {
    1: "normal",
    2: "warning",
    3: "alarm",
}

MODE_MAP = {
    0: "off",
    1: "sleeping",
    2: "startup",
    3: "running",
    4: "derating",
    5: "shutting_down",
    6: "shutdown",
    7: "service",
}


@dataclass(frozen=True, kw_only=True)
class DlxSensorDescription(SensorEntityDescription):
    """Describes a single Danfoss DLX eNEXUS data point."""

    enexus_id: str
    datatype: str
    extra_path: str | None = None  # e.g. "n:4" for the energy-stats group
    divisor: float = 1
    value_map: dict[int, str] | None = None


SENSOR_TYPES: tuple[DlxSensorDescription, ...] = (
    DlxSensorDescription(
        key="power_ac",
        translation_key="power_ac",
        enexus_id="0010",
        datatype="INT16U",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DlxSensorDescription(
        key="power_dc",
        translation_key="power_dc",
        enexus_id="0007",
        datatype="INT16U",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="reactive_power",
        translation_key="reactive_power",
        enexus_id="0082",
        datatype="INT16U",
        native_unit_of_measurement="var",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        enexus_id="0013",
        datatype="INT32S",
        divisor=1000,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    DlxSensorDescription(
        key="energy_month",
        translation_key="energy_month",
        enexus_id="0014",
        datatype="INT32S",
        divisor=1000,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="energy_year",
        translation_key="energy_year",
        enexus_id="0015",
        datatype="INT32S",
        divisor=1000,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        enexus_id="0043",
        extra_path="n:4",
        datatype="INT32U",
        divisor=1000,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    DlxSensorDescription(
        key="peak_power_today",
        translation_key="peak_power_today",
        enexus_id="0040",
        extra_path="n:9",
        datatype="INT32U",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="dc_voltage",
        translation_key="dc_voltage",
        enexus_id="0006",
        datatype="INT16U",
        divisor=10,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="dc_current",
        translation_key="dc_current",
        enexus_id="0005",
        datatype="INT16U",
        divisor=1000,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="ac_voltage",
        translation_key="ac_voltage",
        enexus_id="0009",
        datatype="INT16U",
        divisor=10,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="ac_current",
        translation_key="ac_current",
        enexus_id="0008",
        datatype="INT16U",
        divisor=1000,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="ac_frequency",
        translation_key="ac_frequency",
        enexus_id="0046",
        datatype="INT16U",
        divisor=100,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="temperature",
        translation_key="temperature",
        enexus_id="0045",
        datatype="INT16S",
        divisor=100,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="operating_hours",
        translation_key="operating_hours",
        enexus_id="0011",
        datatype="INT32U",
        divisor=3600,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="insulation_resistance",
        translation_key="insulation_resistance",
        enexus_id="0012",
        datatype="INT16U",
        native_unit_of_measurement="kOhm",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    DlxSensorDescription(
        key="status",
        translation_key="status",
        enexus_id="0001",
        datatype="INT8U",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATUS_MAP.values()),
        value_map=STATUS_MAP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DlxSensorDescription(
        key="mode",
        translation_key="mode",
        enexus_id="0002",
        datatype="INT8U",
        device_class=SensorDeviceClass.ENUM,
        options=list(MODE_MAP.values()),
        value_map=MODE_MAP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
