"""
Backend — todas as chamadas ao sistema Windows.
PowerShell, WMIC, WinAPI, Registro.
"""
import subprocess, json, re, os, platform, shutil, tempfile
try: import winreg
except ImportError: winreg = None
from datetime import datetime

IS_WIN = platform.system() == "Windows"

# ── Helpers ───────────────────────────────────────────────────────────────────
def ps(cmd, timeout=60):
    if not IS_WIN: return "", 0
    try:
        r = subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",cmd],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e: return str(e), -1

def ps_json(cmd, timeout=60):
    out, code = ps(cmd, timeout)
    if not out: return []
    try:
        if out.startswith("{"): out = f"[{out}]"
        r = json.loads(out)
        return r if isinstance(r, list) else [r]
    except: return []

def wmic(q):
    try:
        r = subprocess.run(["wmic"]+q.split()+["get","/format:list"],
                           capture_output=True,text=True,timeout=12)
        return r.stdout
    except: return ""

def field(block, key):
    for line in block.splitlines():
        line=line.strip()
        if line.lower().startswith(key.lower()+"="):
            return line.split("=",1)[1].strip() or "—"
    return "—"

def blocks(text):
    return [b for b in re.split(r'\n\s*\n', text.strip()) if b.strip()]

def date_wmi(raw):
    try: return f"{raw[6:8]}/{raw[4:6]}/{raw[:4]}"
    except: return raw


# ══════════════════════════════════════════════════════════════════════════════
# HARDWARE
# ══════════════════════════════════════════════════════════════════════════════
def get_hardware():
    hw = {}
    # OS
    o = wmic("os Caption,Version,BuildNumber,OSArchitecture")
    hw["os"] = {"name": field(o,"Caption"), "build": field(o,"BuildNumber"),
                "arch": field(o,"OSArchitecture"), "version": field(o,"Version")}
    # CPU
    c = wmic("cpu Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed")
    hw["cpu"] = {"name": field(c,"Name"), "vendor": field(c,"Manufacturer"),
                 "cores": field(c,"NumberOfCores"), "threads": field(c,"NumberOfLogicalProcessors"),
                 "mhz": field(c,"MaxClockSpeed")}
    # GPU
    gpus=[]
    g = wmic("path win32_VideoController Name,DriverVersion,AdapterRAM,PNPDeviceID")
    for blk in blocks(g):
        nm=field(blk,"Name")
        if nm=="—": continue
        n=nm.upper()
        v="NVIDIA" if "NVIDIA" in n else "AMD" if "AMD" in n or "RADEON" in n else "Intel" if "INTEL" in n else "Outro"
        try: vr=f"{int(field(blk,'AdapterRAM'))//1048576} MB"
        except: vr="—"
        gpus.append({"name":nm,"vendor":v,"driver":field(blk,"DriverVersion"),"vram":vr,"pnp":field(blk,"PNPDeviceID")})
    hw["gpu"] = gpus or [{"name":"Não detectado","vendor":"—","driver":"—","vram":"—"}]
    # MB/BIOS
    mb=wmic("baseboard Manufacturer,Product,Version")
    bi=wmic("bios Manufacturer,SMBIOSBIOSVersion,ReleaseDate")
    hw["mb"] = {"vendor":field(mb,"Manufacturer"),"model":field(mb,"Product"),
                "bios":field(bi,"SMBIOSBIOSVersion"),"bios_date":date_wmi(field(bi,"ReleaseDate")),
                "bios_vendor":field(bi,"Manufacturer")}
    # RAM
    slots,total=[],0
    rm=wmic("memorychip Capacity,Speed,Manufacturer,PartNumber")
    for blk in blocks(rm):
        cap=field(blk,"Capacity")
        try: gb=int(cap)/1073741824; total+=gb
        except: gb=0
        slots.append({"gb":f"{gb:.0f} GB","speed":field(blk,"Speed"),"vendor":field(blk,"Manufacturer")})
    hw["ram"]={"total":f"{total:.0f} GB","slots":slots}
    # Disk
    disks=[]
    dk=wmic("diskdrive Model,Size,InterfaceType,FirmwareRevision")
    for blk in blocks(dk):
        m=field(blk,"Model")
        if m=="—": continue
        try: sz=f"{int(field(blk,'Size'))//1073741824} GB"
        except: sz="—"
        disks.append({"model":m,"size":sz,"interface":field(blk,"InterfaceType"),"fw":field(blk,"FirmwareRevision")})
    hw["disk"]=disks
    # Net
    nets=[]
    skip=["microsoft","wan miniport","loopback","bluetooth","virtual","hyper-v","teredo"]
    nt=wmic("nic Name,Manufacturer,MACAddress,Speed,PNPDeviceID")
    for blk in blocks(nt):
        nm=field(blk,"Name")
        if nm=="—" or any(s in nm.lower() for s in skip): continue
        nets.append({"name":nm,"vendor":field(blk,"Manufacturer"),"mac":field(blk,"MACAddress")})
    hw["net"]=nets
    # Audio
    au=wmic("sounddev Name,Manufacturer,DriverVersion")
    hw["audio"]=[{"name":field(b,"Name"),"driver":field(b,"DriverVersion")} for b in blocks(au) if field(b,"Name")!="—"]
    return hw


# ══════════════════════════════════════════════════════════════════════════════
# WINDOWS UPDATE
# ══════════════════════════════════════════════════════════════════════════════
def get_pending_updates():
    if not IS_WIN: return _mock_pending()
    script="""
$S=$null;try{$S=New-Object -ComObject Microsoft.Update.Session}catch{Write-Output '[]';exit}
$R=$S.CreateUpdateSearcher().Search("IsInstalled=0 AND IsHidden=0")
$out=@();foreach($u in $R.Updates){
  $kbs=($u.KBArticleIDs|ForEach-Object{"KB$_"})-join", "
  $isdrv=($u.Categories|Where-Object{$_.Name -like "*Driver*"})-ne $null
  $out+=[PSCustomObject]@{Title=$u.Title;KB=$kbs;SizeMB=[math]::Round($u.MaxDownloadSize/1MB,1);
    UpdateID=$u.Identity.UpdateID;Severity=if($u.MsrcSeverity){$u.MsrcSeverity}else{"Normal"};
    IsDriver=$isdrv;Description=($u.Description-replace'"','')-replace"`n"," "}}
if($out.Count-eq 0){Write-Output'[]'}else{$out|ConvertTo-Json -Depth 2}
"""
    items=ps_json(script,120)
    return [{"title":i.get("Title",""),"kb":i.get("KB",""),"size_mb":i.get("SizeMB",0),
             "update_id":i.get("UpdateID",""),"severity":i.get("Severity","Normal"),
             "is_driver":i.get("IsDriver",False),"description":i.get("Description","")} for i in items]

def get_installed_updates():
    if not IS_WIN: return _mock_installed()
    script="""
$S=New-Object -ComObject Microsoft.Update.Session
$H=$S.CreateUpdateSearcher()
$C=$H.GetTotalHistoryCount()
$items=$H.QueryHistory(0,[Math]::Min($C,200))
$out=@();foreach($u in $items){
  if($u.ResultCode-ne 2){continue}
  $out+=[PSCustomObject]@{Title=$u.Title;Date=$u.Date.ToString("yyyy-MM-dd");
    KB=if($u.Title-match'KB([0-9]+)'){"KB$($Matches[1])"}else{""};
    Type=if($u.Categories|Where-Object{$_.Name-like"*Driver*"}){"Driver"}else{"Sistema"};
    UpdateID=$u.UpdateIdentity.UpdateID}}
if($out.Count-eq 0){Write-Output'[]'}else{$out|ConvertTo-Json -Depth 2}
"""
    items=ps_json(script,60)
    return [{"title":i.get("Title",""),"kb":i.get("KB",""),"date":i.get("Date",""),
             "type":i.get("Type","Sistema"),"update_id":i.get("UpdateID","")} for i in items]

def install_updates(update_ids):
    if not IS_WIN or not update_ids: return True,"Simulado"
    ids = json.dumps(update_ids)
    script = f"""
$IDs = {ids} | ConvertFrom-Json
$S = New-Object -ComObject Microsoft.Update.Session
$Searcher = $S.CreateUpdateSearcher()
try {{
    $R = $Searcher.Search("IsInstalled=0 AND IsHidden=0")
}} catch {{
    Write-Output "ERR:$($_.Exception.Message)"; exit 1
}}
$col = New-Object -ComObject Microsoft.Update.UpdateColl
foreach($u in $R.Updates) {{
    if($IDs -contains $u.Identity.UpdateID) {{ $col.Add($u) | Out-Null }}
}}
if($col.Count -eq 0) {{ Write-Output "NONE"; exit 0 }}
$dl = $S.CreateUpdateDownloader()
$dl.Updates = $col
try {{ $dl.Download() }} catch {{ Write-Output "DL_ERR:$($_.Exception.Message)"; exit 1 }}
$ins = New-Object -ComObject Microsoft.Update.Installer
$ins.Updates = $col
try {{
    $res = $ins.Install()
    Write-Output "RC:$($res.ResultCode) Reboot:$($res.RebootRequired)"
}} catch {{
    Write-Output "INS_ERR:$($_.Exception.Message)"; exit 1
}}
"""
    out, code = ps(script, 900)
    ok = ("RC:2" in out) or ("RC:3" in out)
    return ok, out

def uninstall_update(kb):
    if not kb: return False,"Sem KB"
    n=kb.replace("KB","").strip()
    if not IS_WIN: return True,f"Simulado: desinstalado {kb}"
    out,_=ps(f'$r=Start-Process wusa.exe -ArgumentList "/uninstall /kb:{n} /quiet /norestart" -Wait -PassThru;Write-Output "EC:$($r.ExitCode)"',300)
    ok="EC:0" in out or "EC:3010" in out
    return ok, out


# ══════════════════════════════════════════════════════════════════════════════
# LIMPEZA DE DISCO
# ══════════════════════════════════════════════════════════════════════════════
def get_disk_usage():
    info={}
    if IS_WIN:
        out,_=ps("Get-PSDrive -PSProvider FileSystem|Select-Object Name,@{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}},@{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}},@{N='TotalGB';E={[math]::Round(($_.Used+$_.Free)/1GB,2)}}|ConvertTo-Json -Depth 2")
        try:
            if out.startswith("{"): out=f"[{out}]"
            drives=json.loads(out)
            if not isinstance(drives,list): drives=[drives]
            info["drives"]=drives
        except: info["drives"]=[]
    # Pastas temp
    temp_paths=[os.environ.get("TEMP",""),os.environ.get("TMP",""),
                r"C:\Windows\Temp",r"C:\Windows\SoftwareDistribution\Download"]
    total_temp=0
    tinfo=[]
    for p in temp_paths:
        if p and os.path.exists(p):
            sz=_folder_size(p)
            total_temp+=sz
            tinfo.append({"path":p,"mb":round(sz/1048576,1)})
    info["temp_folders"]=tinfo
    info["total_temp_mb"]=round(total_temp/1048576,1)
    return info

def _folder_size(path):
    total=0
    try:
        for r,dirs,files in os.walk(path):
            for f in files:
                try: total+=os.path.getsize(os.path.join(r,f))
                except: pass
    except: pass
    return total

def clean_temp(progress_cb=None):
    cleaned=0
    temp_paths=[os.environ.get("TEMP",""),os.environ.get("TMP",""),
                r"C:\Windows\Temp",r"C:\Windows\SoftwareDistribution\Download"]
    for p in temp_paths:
        if p and os.path.exists(p):
            for item in os.listdir(p):
                fp=os.path.join(p,item)
                try:
                    if os.path.isfile(fp): os.remove(fp); cleaned+=1
                    elif os.path.isdir(fp): shutil.rmtree(fp,ignore_errors=True); cleaned+=1
                except: pass
            if progress_cb: progress_cb(f"Limpando {p}...")
    # Prefetch
    pfetch=r"C:\Windows\Prefetch"
    if os.path.exists(pfetch):
        for f in os.listdir(pfetch):
            try: os.remove(os.path.join(pfetch,f)); cleaned+=1
            except: pass
    return cleaned

def run_disk_cleanup():
    if IS_WIN:
        subprocess.Popen(["cleanmgr.exe","/sagerun:1"])


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAMAS INSTALADOS
# ══════════════════════════════════════════════════════════════════════════════
def get_installed_apps():
    if not IS_WIN: return _mock_apps()
    script="""
$paths=@(
  'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
  'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
  'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
)
$out=@()
foreach($p in $paths){
  try{
    $items=Get-ItemProperty $p -EA SilentlyContinue|Where-Object{$_.DisplayName -and $_.DisplayName -ne ""}
    foreach($i in $items){
      $out+=[PSCustomObject]@{
        Name=$i.DisplayName;Version=$i.DisplayVersion;Publisher=$i.Publisher;
        InstallDate=$i.InstallDate;Size=if($i.EstimatedSize){[math]::Round($i.EstimatedSize/1024,1)}else{0};
        UninstallCmd=$i.UninstallString}}
  }catch{}
}
$out|Sort-Object Name|ConvertTo-Json -Depth 2
"""
    items=ps_json(script,30)
    seen,apps=set(),[]
    for i in items:
        nm=i.get("Name","")
        if not nm or nm in seen: continue
        seen.add(nm)
        apps.append({"name":nm,"version":i.get("Version","—"),"publisher":i.get("Publisher","—"),
                     "install_date":i.get("InstallDate",""),"size_mb":i.get("Size",0),
                     "uninstall_cmd":i.get("UninstallCmd","")})
    return apps

def uninstall_app(cmd):
    if not cmd or not IS_WIN: return False,"Sem comando"
    try:
        # msiexec silencioso
        if "msiexec" in cmd.lower():
            cmd2=re.sub(r'/I','/X',cmd,flags=re.IGNORECASE)
            if "/quiet" not in cmd2.lower(): cmd2+=" /quiet /norestart"
            subprocess.Popen(cmd2, shell=True)
        else:
            subprocess.Popen(cmd, shell=True)
        return True,"Desinstalação iniciada"
    except Exception as e:
        return False,str(e)


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def get_startup_items():
    if not IS_WIN: return _mock_startup()
    script="""
$out=@()
$keys=@(
  @{Path='HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run';Scope='Sistema'},
  @{Path='HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run';Scope='Usuário'}
)
foreach($k in $keys){
  try{
    $props=Get-ItemProperty $k.Path -EA SilentlyContinue
    $props.PSObject.Properties|Where-Object{$_.Name-notmatch'^PS'}|ForEach-Object{
      $out+=[PSCustomObject]@{Name=$_.Name;Command=$_.Value;Scope=$k.Scope;Enabled=$true}}
  }catch{}
}
# Task Scheduler startup
Get-ScheduledTask -EA SilentlyContinue|Where-Object{$_.Settings.ExecutionTimeLimit -ne $null -and $_.Triggers|Where-Object{$_ -is [Microsoft.Management.Infrastructure.CimInstance] -and $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger'}}|ForEach-Object{
  $out+=[PSCustomObject]@{Name=$_.TaskName;Command=$_.TaskPath;Scope='Agendador';Enabled=($_.State-eq'Ready')}}
$out|ConvertTo-Json -Depth 2
"""
    items=ps_json(script,20)
    return [{"name":i.get("Name",""),"command":i.get("Command",""),
             "scope":i.get("Scope",""),"enabled":i.get("Enabled",True)} for i in items if i.get("Name")]

def set_startup_enabled(name, scope, enabled):
    key_path=("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" if scope=="Sistema"
              else "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run")
    hive=(winreg.HKEY_LOCAL_MACHINE if scope=="Sistema" else winreg.HKEY_CURRENT_USER)
    # Guardar em RunOnce desabilitado vs mover
    disabled_path="SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved\\Run"
    if not IS_WIN: return True
    try:
        if enabled:
            ps(f'Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{name}" -Value "" -EA SilentlyContinue')
        else:
            ps(f'Remove-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{name}" -EA SilentlyContinue')
        return True
    except: return False


# ══════════════════════════════════════════════════════════════════════════════
# REDE
# ══════════════════════════════════════════════════════════════════════════════
def get_network_info():
    info={"adapters":[],"dns":[],"ip_public":"—"}
    if not IS_WIN: return _mock_network()
    script="""
Get-NetIPConfiguration|Select-Object InterfaceAlias,
  @{N='IP';E={$_.IPv4Address.IPAddress}},
  @{N='Gateway';E={$_.IPv4DefaultGateway.NextHop}},
  @{N='DNS';E={($_.DNSServer.ServerAddresses)-join', '}},
  @{N='MAC';E={$_.NetAdapter.MacAddress}},
  @{N='Status';E={$_.NetAdapter.Status}},
  @{N='Speed';E={$_.NetAdapter.LinkSpeed}}|ConvertTo-Json -Depth 2
"""
    items=ps_json(script,20)
    info["adapters"]=items
    # DNS atual
    dns_out,_=ps("Get-DnsClientServerAddress -AddressFamily IPv4|Select-Object InterfaceAlias,ServerAddresses|ConvertTo-Json -Depth 2")
    try:
        if dns_out.startswith("{"): dns_out=f"[{dns_out}]"
        info["dns"]=json.loads(dns_out) if dns_out else []
    except: pass
    # IP público
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org",timeout=5) as r:
            info["ip_public"]=r.read().decode()
    except: pass
    return info

def set_dns(adapter, primary, secondary=""):
    dns=f'"{primary}"' + (f',"{secondary}"' if secondary else "")
    out,code=ps(f'Set-DnsClientServerAddress -InterfaceAlias "{adapter}" -ServerAddresses ({dns})',30)
    return code==0, out

def flush_dns():
    out,code=ps("ipconfig /flushdns",15)
    return code==0, out

def run_ping(host="google.com"):
    out,_=ps(f"Test-Connection -ComputerName {host} -Count 4|Select-Object Address,Latency|ConvertTo-Json",15)
    return out

def reset_network():
    cmds=["netsh winsock reset","netsh int ip reset","ipconfig /release","ipconfig /flushdns","ipconfig /renew"]
    for c in cmds: ps(c,20)
    return True


# ══════════════════════════════════════════════════════════════════════════════
# SERVIÇOS
# ══════════════════════════════════════════════════════════════════════════════
def get_services():
    if not IS_WIN: return _mock_services()
    script = """
Get-WmiObject Win32_Service | Select-Object `
    Name, DisplayName,
    @{N='Status';    E={ $_.State }},
    @{N='StartType'; E={ if($_.StartMode -eq 'Auto'){'Automatic'} elseif($_.StartMode -eq 'Manual'){'Manual'} else{'Disabled'} }},
    @{N='Running';   E={ $_.State -eq 'Running' }} |
Sort-Object DisplayName | ConvertTo-Json -Depth 2
"""
    items = ps_json(script, 30)
    return [{"name": i.get("Name",""), "display": i.get("DisplayName",""),
             "status": i.get("Status",""), "start_type": i.get("StartType",""),
             "running": bool(i.get("Running", False))} for i in items]

def service_action(name, action):
    """action: start | stop | restart | disable | auto"""
    cmds={"start":f"Start-Service '{name}'","stop":f"Stop-Service '{name}' -Force",
          "restart":f"Restart-Service '{name}' -Force",
          "disable":f"Set-Service '{name}' -StartupType Disabled",
          "auto":f"Set-Service '{name}' -StartupType Automatic"}
    if action not in cmds: return False,"Ação inválida"
    out,code=ps(cmds[action],30)
    return code==0, out


# ══════════════════════════════════════════════════════════════════════════════
# PONTO DE RESTAURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def get_restore_points():
    if not IS_WIN: return _mock_restore()
    script="Get-ComputerRestorePoint|Select-Object Description,CreationTime,SequenceNumber|ConvertTo-Json -Depth 2"
    items=ps_json(script,20)
    return [{"desc":i.get("Description",""),"date":str(i.get("CreationTime",""))[:19],
             "seq":i.get("SequenceNumber",0)} for i in items]

def create_restore_point(desc="Alphas Gerenciador"):
    out,code=ps(f'Checkpoint-Computer -Description "{desc}" -RestorePointType MODIFY_SETTINGS',120)
    return code==0, out

def restore_to_point(seq):
    out,code=ps(f"Restore-Computer -RestorePoint {seq} -Confirm:$false",30)
    return code==0, out


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP
# ══════════════════════════════════════════════════════════════════════════════
def backup_files(source, destination, progress_cb=None):
    try:
        os.makedirs(destination, exist_ok=True)
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        dest=os.path.join(destination,f"backup_{stamp}")
        shutil.copytree(source, dest)
        return True,f"Backup criado em: {dest}"
    except Exception as e:
        return False,str(e)

def open_backup_settings():
    ps("Start-Process ms-settings:backup",5)


# ══════════════════════════════════════════════════════════════════════════════
# MODO DEUS (God Mode)
# ══════════════════════════════════════════════════════════════════════════════
GOD_MODE_CLSID="{ED7BA470-8E54-465E-825C-99712043E01C}"

def create_god_mode(path=None):
    if not path:
        desktop=os.path.join(os.path.expanduser("~"),"Desktop")
        path=os.path.join(desktop,f"GodMode.{GOD_MODE_CLSID}")
    try:
        os.makedirs(path, exist_ok=True)
        return True,path
    except Exception as e:
        return False,str(e)

# Todas as categorias do God Mode com seus comandos ms-settings / shell
GOD_MODE_ITEMS = [
    # (Categoria, Nome, Comando)
    ("🔧 Sistema","Sobre o PC","ms-settings:about"),
    ("🔧 Sistema","Exibição","ms-settings:display"),
    ("🔧 Sistema","Som","ms-settings:sound"),
    ("🔧 Sistema","Notificações","ms-settings:notifications"),
    ("🔧 Sistema","Multitarefa","ms-settings:multitasking"),
    ("🔧 Sistema","Armazenamento","ms-settings:storagesense"),
    ("🔧 Sistema","Energia","ms-settings:powersleep"),
    ("🔧 Sistema","Bateria","ms-settings:batterysaver"),
    ("🔧 Sistema","Área de Trabalho Remota","ms-settings:remotedesktop"),
    ("🔧 Sistema","Resolução de Problemas","ms-settings:troubleshoot"),
    ("🔧 Sistema","Projetar para este PC","ms-settings:project"),
    ("🌐 Rede","Wi-Fi","ms-settings:network-wifi"),
    ("🌐 Rede","Ethernet","ms-settings:network-ethernet"),
    ("🌐 Rede","VPN","ms-settings:network-vpn"),
    ("🌐 Rede","Proxy","ms-settings:network-proxy"),
    ("🌐 Rede","Status de Rede","ms-settings:network-status"),
    ("🌐 Rede","Ponto de Acesso Móvel","ms-settings:network-mobilehotspot"),
    ("🌐 Rede","Uso de Dados","ms-settings:datausage"),
    ("🎨 Personalização","Fundo","ms-settings:personalization-background"),
    ("🎨 Personalização","Cores","ms-settings:colors"),
    ("🎨 Personalização","Tela de Bloqueio","ms-settings:lockscreen"),
    ("🎨 Personalização","Temas","ms-settings:themes"),
    ("🎨 Personalização","Barra de Tarefas","ms-settings:taskbar"),
    ("🎨 Personalização","Menu Iniciar","ms-settings:personalization-start"),
    ("🎨 Personalização","Fontes","ms-settings:fonts"),
    ("📱 Apps","Apps Padrão","ms-settings:defaultapps"),
    ("📱 Apps","Apps e Recursos","ms-settings:appsfeatures"),
    ("📱 Apps","Apps de Inicialização","ms-settings:startupapps"),
    ("📱 Apps","Mapas Offline","ms-settings:maps"),
    ("📱 Apps","Reprodução Automática","ms-settings:autoplay"),
    ("👤 Contas","Suas Informações","ms-settings:yourinfo"),
    ("👤 Contas","E-mail e Contas","ms-settings:emailandaccounts"),
    ("👤 Contas","Opções de Entrada","ms-settings:signinoptions"),
    ("👤 Contas","Família e Outros","ms-settings:otherusers"),
    ("👤 Contas","Sincronizar Configurações","ms-settings:sync"),
    ("⏰ Hora","Data e Hora","ms-settings:dateandtime"),
    ("⏰ Hora","Idioma e Região","ms-settings:regionlanguage"),
    ("⏰ Hora","Idioma","ms-settings:regionlanguage"),
    ("🕹 Jogos","Barra de Jogos","ms-settings:gaming-gamebar"),
    ("🕹 Jogos","Modo Jogo","ms-settings:gaming-gamemode"),
    ("🕹 Jogos","Captura","ms-settings:gaming-gamedvr"),
    ("♿ Acessibilidade","Narrador","ms-settings:easeofaccess-narrator"),
    ("♿ Acessibilidade","Lupa","ms-settings:easeofaccess-magnifier"),
    ("♿ Acessibilidade","Alto Contraste","ms-settings:easeofaccess-highcontrast"),
    ("♿ Acessibilidade","Teclado","ms-settings:easeofaccess-keyboard"),
    ("♿ Acessibilidade","Mouse","ms-settings:easeofaccess-mouse"),
    ("♿ Acessibilidade","Cursor e Ponteiro","ms-settings:easeofaccess-cursorandpointersize"),
    ("🔒 Privacidade","Geral","ms-settings:privacy"),
    ("🔒 Privacidade","Localização","ms-settings:privacy-location"),
    ("🔒 Privacidade","Câmera","ms-settings:privacy-webcam"),
    ("🔒 Privacidade","Microfone","ms-settings:privacy-microphone"),
    ("🔒 Privacidade","Diagnóstico","ms-settings:privacy-feedback"),
    ("🔒 Privacidade","Histórico de Atividades","ms-settings:privacy-activityhistory"),
    ("🔄 Atualização","Windows Update","ms-settings:windowsupdate"),
    ("🔄 Atualização","Segurança do Windows","ms-settings:windowsdefender"),
    ("🔄 Atualização","Backup","ms-settings:backup"),
    ("🔄 Atualização","Recuperação","ms-settings:recovery"),
    ("🔄 Atualização","Ativação","ms-settings:activation"),
    ("🔄 Atualização","Encontrar Meu Dispositivo","ms-settings:findmydevice"),
    ("🛠 Ferramentas","Gerenc. de Dispositivos","devmgmt.msc"),
    ("🛠 Ferramentas","Gerenc. de Disco","diskmgmt.msc"),
    ("🛠 Ferramentas","Serviços","services.msc"),
    ("🛠 Ferramentas","Editor de Registro","regedit"),
    ("🛠 Ferramentas","Política de Grupo","gpedit.msc"),
    ("🛠 Ferramentas","Informações do Sistema","msinfo32"),
    ("🛠 Ferramentas","Monitor de Desempenho","perfmon"),
    ("🛠 Ferramentas","Visualizador de Eventos","eventvwr"),
    ("🛠 Ferramentas","Firewall","WF.msc"),
    ("🛠 Ferramentas","Programas e Recursos","appwiz.cpl"),
    ("🛠 Ferramentas","Opções de Internet","inetcpl.cpl"),
    ("🛠 Ferramentas","Contas de Usuário","netplwiz"),
    ("🛠 Ferramentas","Configuração do Sistema","msconfig"),
    ("🛠 Ferramentas","Limpeza de Disco","cleanmgr"),
    ("🛠 Ferramentas","Desfragmentador","dfrgui"),
    ("🛠 Ferramentas","Verificação de Arquivos","sfc /scannow"),
    ("🛠 Ferramentas","Painel de Controle","control"),
]

def open_god_mode_item(cmd):
    if not IS_WIN: return
    if cmd.startswith("ms-settings:"):
        subprocess.Popen(["start","",cmd], shell=True)
    elif " " in cmd or "/" in cmd:
        # comando com argumentos (sfc /scannow)
        subprocess.Popen(["powershell","-Command",f"Start-Process cmd -ArgumentList '/k {cmd}' -Verb RunAs"])
    else:
        subprocess.Popen(["start","",cmd], shell=True)


# ══════════════════════════════════════════════════════════════════════════════
# DRIVERS (Gerenciador de Dispositivos)
# ══════════════════════════════════════════════════════════════════════════════
def get_drivers_device_manager():
    """Lista drivers igual ao Gerenciador de Dispositivos do Windows."""
    if not IS_WIN: return _mock_drivers_dm()
    script = """
Get-WmiObject Win32_PnPSignedDriver |
  Where-Object { $_.DeviceName -and $_.DeviceName -ne '' } |
  Select-Object DeviceName, Manufacturer, DriverVersion, DriverDate,
    @{N='DeviceClass'; E={ $_.DeviceClass }},
    @{N='IsSigned';    E={ $_.IsSigned }},
    @{N='Status';      E={
        $dev = Get-WmiObject Win32_PnPEntity -Filter "Name='$($_.DeviceName)'" -EA SilentlyContinue | Select-Object -First 1
        if($dev) { $dev.Status } else { 'OK' }
    }} |
Sort-Object DeviceClass, DeviceName |
ConvertTo-Json -Depth 2
"""
    items = ps_json(script, 60)
    result = []
    for i in items:
        nm = i.get("DeviceName","")
        if not nm: continue
        # formata data do driver
        raw_date = str(i.get("DriverDate",""))
        fmt_date = "—"
        if raw_date and len(raw_date) >= 8:
            try:
                y,m,d = raw_date[:4], raw_date[4:6], raw_date[6:8]
                fmt_date = f"{d}/{m}/{y}"
            except: pass
        result.append({
            "name":    nm,
            "class":   i.get("DeviceClass","Outros") or "Outros",
            "vendor":  i.get("Manufacturer","—") or "—",
            "version": i.get("DriverVersion","—") or "—",
            "date":    fmt_date,
            "signed":  bool(i.get("IsSigned", False)),
            "status":  i.get("Status","OK") or "OK",
        })
    return result

def _mock_drivers_dm():
    return [
        {"name":"NVIDIA GeForce RTX 3070","class":"Display","vendor":"NVIDIA","version":"546.33.0.0","date":"15/11/2023","signed":True,"status":"OK"},
        {"name":"Intel(R) Wi-Fi 6 AX200","class":"Net","vendor":"Intel","version":"22.190.0.7","date":"10/01/2024","signed":True,"status":"OK"},
        {"name":"Realtek High Definition Audio","class":"MEDIA","vendor":"Realtek","version":"6.0.9455.1","date":"05/09/2023","signed":True,"status":"OK"},
        {"name":"Intel(R) USB 3.0 eXtensible Host Controller","class":"USB","vendor":"Intel","version":"5.0.4.43","date":"20/03/2023","signed":True,"status":"OK"},
        {"name":"Logitech USB Input Device","class":"HIDClass","vendor":"Logitech","version":"12.0.0.0","date":"01/01/2023","signed":True,"status":"OK"},
        {"name":"Generic PnP Monitor","class":"Monitor","vendor":"(Monitor Padrão)","version":"10.0.22621.1","date":"01/11/2022","signed":True,"status":"OK"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# RECURSOS DO WINDOWS (Windows Features)
# ══════════════════════════════════════════════════════════════════════════════
def get_windows_features():
    if not IS_WIN: return _mock_windows_features()
    script = """
try {
    $feats = Get-WindowsOptionalFeature -Online -EA Stop |
        Select-Object FeatureName,
            @{N='Display'; E={ ($_.FeatureName -replace '-',' ') }},
            @{N='Enabled'; E={ $_.State -eq 'Enabled' }} |
        Sort-Object Display
    $feats | ConvertTo-Json -Depth 2
} catch {
    # Fallback para DISM via cmd
    $out = dism /online /get-features /format:list 2>$null
    $lines = $out -split "`n"
    $result = @()
    $current = @{}
    foreach($l in $lines) {
        if($l -match "^Feature Name : (.+)$") {
            if($current.name) { $result += $current }
            $current = @{ name=$Matches[1].Trim(); display=($Matches[1].Trim() -replace '-',' '); enabled=$false }
        } elseif($l -match "^State : Enabled") { $current.enabled = $true }
    }
    if($current.name) { $result += $current }
    $result | ConvertTo-Json -Depth 2
}
"""
    items = ps_json(script, 120)
    result = []
    for i in items:
        nm = i.get("FeatureName","") or i.get("name","")
        if not nm: continue
        disp = i.get("Display","") or i.get("display","") or nm.replace("-"," ")
        result.append({
            "name":    nm,
            "display": disp,
            "enabled": bool(i.get("Enabled", i.get("enabled", False))),
        })
    return result

def toggle_windows_feature(feature_name, enable):
    if not IS_WIN: return True, "Simulado"
    action = "Enable" if enable else "Disable"
    script = f"""
try {{
    {action}-WindowsOptionalFeature -Online -FeatureName "{feature_name}" -NoRestart -EA Stop | Out-Null
    Write-Output "OK"
}} catch {{
    Write-Output "ERR:$($_.Exception.Message)"
}}
"""
    out, code = ps(script, 300)
    ok = "OK" in out and "ERR:" not in out
    return ok, out

def _mock_windows_features():
    return [
        {"name":"IIS-WebServer","display":"IIS Web Server","enabled":False},
        {"name":"Microsoft-Hyper-V","display":"Microsoft Hyper V","enabled":False},
        {"name":"Microsoft-Windows-Subsystem-Linux","display":"Windows Subsystem for Linux","enabled":True},
        {"name":"TelnetClient","display":"Telnet Client","enabled":False},
        {"name":"TFTP","display":"TFTP Client","enabled":False},
        {"name":"NetFx3","display":".NET Framework 3.5","enabled":True},
        {"name":"VirtualMachinePlatform","display":"Virtual Machine Platform","enabled":True},
        {"name":"Containers-DisposableClientVM","display":"Windows Sandbox","enabled":False},
        {"name":"Microsoft-Windows-Printing-PrintToPDFServices-Package","display":"Microsoft Print to PDF","enabled":True},
        {"name":"WorkFolders-Client","display":"Work Folders Client","enabled":False},
    ]



def _mock_pending():
    return [
        {"title":"Driver NVIDIA GeForce RTX 3070 546.33","kb":"KB5034441","size_mb":621.4,
         "update_id":"aaa-111","severity":"Recomendado","is_driver":True,"description":"Driver GPU NVIDIA"},
        {"title":"Atualização Cumulativa Windows 11 22H2 (KB5035853)","kb":"KB5035853","size_mb":312.1,
         "update_id":"bbb-222","severity":"Crítico","is_driver":False,"description":"Correções de segurança"},
        {"title":"Intel Ethernet Adapter Driver 12.19.2.36","kb":"KB5032310","size_mb":14.5,
         "update_id":"ccc-333","severity":"Normal","is_driver":True,"description":"Driver de rede Intel"},
        {"title":"Realtek HD Audio Driver 6.0.9455.1","kb":"","size_mb":88.2,
         "update_id":"ddd-444","severity":"Normal","is_driver":True,"description":"Driver de áudio"},
    ]

def _mock_installed():
    return [
        {"title":"Atualização de Segurança (KB5034843)","kb":"KB5034843","date":"2024-03-12","type":"Sistema","update_id":"e01"},
        {"title":"Driver Intel HD Graphics 31.0.101.4146","kb":"KB5031354","date":"2024-02-20","type":"Driver","update_id":"e02"},
        {"title":".NET Framework 4.8 (KB5032929)","kb":"KB5032929","date":"2024-01-10","type":"Sistema","update_id":"e03"},
        {"title":"Microsoft Defender (KB2267602)","kb":"KB2267602","date":"2024-03-15","type":"Sistema","update_id":"e04"},
        {"title":"Driver Realtek Audio 6.0.9300.1","kb":"","date":"2023-12-05","type":"Driver","update_id":"e05"},
    ]

def _mock_apps():
    return [
        {"name":"Google Chrome","version":"122.0.6261.112","publisher":"Google LLC","install_date":"20240101","size_mb":350,"uninstall_cmd":""},
        {"name":"Microsoft Visual C++ 2022","version":"14.38.33130","publisher":"Microsoft","install_date":"20231015","size_mb":25,"uninstall_cmd":""},
        {"name":"VLC media player","version":"3.0.20","publisher":"VideoLAN","install_date":"20230801","size_mb":95,"uninstall_cmd":""},
        {"name":"7-Zip 23.01","version":"23.01","publisher":"Igor Pavlov","install_date":"20230601","size_mb":5,"uninstall_cmd":""},
        {"name":"Discord","version":"1.0.9023","publisher":"Discord Inc.","install_date":"20240201","size_mb":220,"uninstall_cmd":""},
        {"name":"Steam","version":"","publisher":"Valve Corporation","install_date":"20221101","size_mb":1200,"uninstall_cmd":""},
    ]

def _mock_startup():
    return [
        {"name":"Discord","command":"C:\\Users\\User\\AppData\\Local\\Discord\\app-1.0.9023\\Discord.exe","scope":"Usuário","enabled":True},
        {"name":"Steam","command":"C:\\Program Files (x86)\\Steam\\steam.exe -silent","scope":"Sistema","enabled":True},
        {"name":"OneDrive","command":"C:\\Users\\User\\AppData\\Local\\Microsoft\\OneDrive\\OneDrive.exe","scope":"Usuário","enabled":False},
        {"name":"Spotify","command":"C:\\Users\\User\\AppData\\Roaming\\Spotify\\Spotify.exe","scope":"Usuário","enabled":True},
    ]

def _mock_network():
    return {"adapters":[{"InterfaceAlias":"Ethernet","IP":"192.168.1.100","Gateway":"192.168.1.1","DNS":"8.8.8.8, 8.8.4.4","MAC":"AA-BB-CC-DD-EE-FF","Status":"Up","Speed":"1 Gbps"}],
            "dns":[{"InterfaceAlias":"Ethernet","ServerAddresses":["8.8.8.8","8.8.4.4"]}],"ip_public":"186.xxx.xxx.xxx"}

def _mock_services():
    return [
        {"name":"Spooler","display":"Spooler de Impressão","status":"Running","start_type":"Automatic"},
        {"name":"wuauserv","display":"Windows Update","status":"Running","start_type":"Manual"},
        {"name":"WSearch","display":"Windows Search","status":"Running","start_type":"Automatic"},
        {"name":"Themes","display":"Temas","status":"Running","start_type":"Automatic"},
        {"name":"XblGameSave","display":"Xbox Game Save","status":"Stopped","start_type":"Manual"},
        {"name":"DiagTrack","display":"Experiências do Usuário Conectado","status":"Running","start_type":"Automatic"},
        {"name":"SysMain","display":"SysMain (Superfetch)","status":"Running","start_type":"Automatic"},
        {"name":"WinDefend","display":"Microsoft Defender Antivirus","status":"Running","start_type":"Automatic"},
    ]

def _mock_restore():
    return [
        {"desc":"Antes de instalar driver NVIDIA","date":"2024-03-10 14:32:00","seq":1},
        {"desc":"Windows Update automático","date":"2024-02-28 10:00:00","seq":2},
        {"desc":"Alphas Gerenciador","date":"2024-03-15 09:15:00","seq":3},
    ]
