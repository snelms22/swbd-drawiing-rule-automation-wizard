"""Writes the AutoCAD add-in: a "Hyper" ribbon tab with a Switchboard Configurator button
(decisions 2026-10-15). Run by the release command; the launcher copies the result into
each person's AutoCAD plug-ins folder.

It is an Autodesk "bundle" folder, which AutoCAD loads by itself at start-up:

    HyperConfigurators.bundle/
        PackageContents.xml           which AutoCAD it loads in, and what to load
        Contents/
            hyper_configurators.lsp   the HYPERSWBD command: starts the launcher
            Hyper.cuix                the ribbon tab, panel and button

It loads only in plain AutoCAD 2026 (Platform "AutoCAD" excludes AutoCAD Electrical and
the other verticals; series R25.1 is 2026, the version the configurator drives).

The .cuix is a zip of small XML parts, written the same way as Autodesk's own partial
menu files (modelled on AppManager.cuix): MenuGroup.cui holds the command macro,
RibbonRoot.cui the tab -> panel -> button that runs it.
"""
import zipfile
from pathlib import Path

BUNDLE_NAME = "HyperConfigurators.bundle"
COMMAND = "HYPERSWBD"
TAB_TEXT = "Hyper"
PANEL_TEXT = "Configurators"
BUTTON_TEXT = "Switchboard Configurator"
# Each person's launcher (installed by the launcher itself, see launcher.py).
LAUNCHER_IN_LOCALAPPDATA = r"Hyper Configurators\Switchboard Configurator\Switchboard Configurator.exe"

# Fixed ids (GUIDs) so a newer bundle replaces the older one instead of sitting beside it.
PRODUCT_CODE = "{6F1B6E52-3C55-4C2D-9D4C-2B7A4E1F5A01}"
UPGRADE_CODE = "{0B7D0C44-8E7A-4F0F-A0B1-5C2E9D3A7B02}"

XML_HEADER = '<?xml version="1.0" encoding="utf-8"?>\n'
CUI_NAMESPACES = ('xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
                  'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
REV = '<ModifiedRev MajorVersion="25" MinorVersion="1" UserVersion="0" />'


def package_contents(app_version: str) -> str:
    return XML_HEADER + f"""<ApplicationPackage SchemaVersion="1.0" AutodeskProduct="AutoCAD"
    Name="Hyper Configurators" Description="Hyper ribbon tab: Switchboard Configurator"
    AppVersion="{app_version}" Author="Hyper Solutions"
    ProductCode="{PRODUCT_CODE}" UpgradeCode="{UPGRADE_CODE}">
  <CompanyDetails Name="Hyper Solutions" />
  <Components Description="AutoCAD 2026">
    <RuntimeRequirements OS="Win64" Platform="AutoCAD" SeriesMin="R25.1" SeriesMax="R25.1" />
    <ComponentEntry AppName="HyperConfiguratorsCommands" ModuleName="./Contents/hyper_configurators.lsp"
        AppDescription="HYPERSWBD command" LoadOnAutoCADStartup="True" />
    <ComponentEntry AppName="HyperConfiguratorsRibbon" ModuleName="./Contents/Hyper.cuix"
        AppDescription="Hyper ribbon tab" LoadOnAutoCADStartup="True" />
  </Components>
</ApplicationPackage>
"""


def lisp_commands() -> str:
    launcher = LAUNCHER_IN_LOCALAPPDATA.replace("\\", "\\\\")
    return f""";; Hyper Configurators: commands for the Hyper ribbon tab. Written by the release
;; command (distribution/autocad_addin.py); do not edit here.
(defun c:{COMMAND} (/ launcher)
  (setq launcher (strcat (getenv "LOCALAPPDATA") "\\\\{launcher}"))
  (if (findfile launcher)
    (startapp (strcat "\\"" launcher "\\""))
    (alert "Switchboard Configurator is not installed on this PC.\\nRun 'Install Switchboard Configurator' from the CONFIGURATORS folder in SharePoint.")
  )
  (princ)
)
(princ)
"""


def _menu_group() -> str:
    return f"""<?xml version="1.0"?>
<MenuGroup {CUI_NAMESPACES} Name="HYPER" DisplayName="HYPER">
  <MacroGroup Name="HyperMacros" Citizen="A">
    <MenuMacro UID="MM_HYPER_SWBD">
      <Macro type="Any">
        {REV}
        <Name UID="XLS_HYPER_SWBD_NAME">{BUTTON_TEXT}</Name>
        <Command>^C^C{COMMAND}</Command>
        <HelpString UID="XLS_HYPER_SWBD_HELP">Opens the Switchboard Configurator</HelpString>
        <SmallImage Name="swbd_16.png" />
        <LargeImage Name="swbd_32.png" />
        <CLICommand UID="XLS_HYPER_SWBD_CLI">{COMMAND}</CLICommand>
      </Macro>
    </MenuMacro>
  </MacroGroup>
</MenuGroup>
"""


def _ribbon_root() -> str:
    return f"""<?xml version="1.0"?>
<RibbonRoot>
  <RibbonPanelSourceCollection {CUI_NAMESPACES}>
    <RibbonPanelSource UID="RBN_HYPER_PANEL" Text="{PANEL_TEXT}" HiddenInEditor="false">
      {REV}
      <Name UID="XLS_HYPER_PANEL_NAME">Hyper - {PANEL_TEXT}</Name>
      <RibbonRow UID="RBN_HYPER_ROW">
        {REV}
        <RibbonCommandButton UID="RBN_HYPER_SWBD" Id="AcRibbonCommandButton" Text="{BUTTON_TEXT}"
            ButtonStyle="LargeWithText" MenuMacroID="MM_HYPER_SWBD" KeyTip="S">
          <TooltipTitle UID="XLS_HYPER_SWBD_TIP">{BUTTON_TEXT}</TooltipTitle>
          {REV}
        </RibbonCommandButton>
      </RibbonRow>
      <RibbonPanelBreak UID="RBN_HYPER_BREAK" Id="AcRibbonPanelBreak">
        {REV}
      </RibbonPanelBreak>
    </RibbonPanelSource>
  </RibbonPanelSourceCollection>
  <RibbonTabSourceCollection>
    <RibbonTabSource Text="{TAB_TEXT}" UID="RBN_HYPER_TAB" KeyTip="HY">
      {REV}
      <Name UID="XLS_HYPER_TAB_NAME">{TAB_TEXT}</Name>
      <RibbonPanelSourceReference UID="RBN_HYPER_PANEL_REF" PanelId="RBN_HYPER_PANEL" ResizeStyle="Default">
        {REV}
      </RibbonPanelSourceReference>
    </RibbonTabSource>
  </RibbonTabSourceCollection>
</RibbonRoot>
"""


def _header() -> str:
    return f"""<?xml version="1.0"?>
<CustSection {CUI_NAMESPACES}>
  <FileVersion MajorVersion="0" MinorVersion="6" IncrementalVersion="1" UserVersion="0" />
  <Header>
    <CommonConfiguration>
      <CommonItems>
        {REV}
      </CommonItems>
    </CommonConfiguration>
  </Header>
</CustSection>
"""


def write_cuix(path: Path, icon_16: Path, icon_32: Path):
    parts = {
        "Header.cui": _header(),
        "MenuGroup.cui": _menu_group(),
        "RibbonRoot.cui": _ribbon_root(),
    }
    images = {"swbd_16.png": icon_16.read_bytes(), "swbd_32.png": icon_32.read_bytes()}
    content_types = XML_HEADER + (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="cui" ContentType="text/xml" />'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
        '<Default Extension="png" ContentType="text/plain" />'
        '<Default Extension="xml" ContentType="text/xml" />'
        '</Types>')
    relationships = [f'<Relationship Type="CUI" Target="/{name}" Id="R{index:016d}" />'
                     for index, name in enumerate(parts, start=1)]
    relationships += [f'<Relationship Type="Image" Target="/{name}" Id="R{index:016d}" />'
                      for index, name in enumerate(images, start=len(parts) + 1)]
    rels = XML_HEADER + ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         + "".join(relationships) + "</Relationships>")
    package_info = XML_HEADER + "<MenuPackageParts>\n" + "".join(
        f'  <PartData PartData_Name="/{name}" PartData_Modified="2026-10-15T00:00:00" />\n'
        for name in [*parts, *images, "Menu_Package_Info.xml"]) + "</MenuPackageParts>\n"

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as cuix:
        cuix.writestr("[Content_Types].xml", content_types)
        cuix.writestr("_rels/.rels", rels)
        for name, text in parts.items():
            cuix.writestr(name, text)
        for name, data in images.items():
            cuix.writestr(name, data)
        cuix.writestr("Menu_Package_Info.xml", package_info)


def write_bundle(destination_folder: Path, app_version: str, assets: Path) -> Path:
    """Write HyperConfigurators.bundle into `destination_folder`. Returns its path."""
    bundle = Path(destination_folder) / BUNDLE_NAME
    contents = bundle / "Contents"
    contents.mkdir(parents=True, exist_ok=True)
    (bundle / "PackageContents.xml").write_text(package_contents(app_version), encoding="utf-8")
    (contents / "hyper_configurators.lsp").write_text(lisp_commands(), encoding="utf-8")
    write_cuix(contents / "Hyper.cuix", assets / "swbd_16.png", assets / "swbd_32.png")
    return bundle
