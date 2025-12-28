import shutil
import os
import sys
import winsdk.windows.management.deployment as deployment
import winsdk.windows.system as ws
import winsdk.windows.foundation as foundation
import asyncio
import ctypes
import webbrowser
import requests
from urllib.parse import unquote
import json
from tkinter import filedialog
import re
import subprocess
import zipfile
import winreg
import threading

# 欢迎部分
os.system('color E0') # 调整颜色
print("欢迎使用Python Minecraft Launcher: Bedrock Edition (Command Line)！")

# 初始化设置
settings = {
    "UWPUnlock": True,
    "GDKUnlock": True,
    "EditorHint": False,
    "GDKDir": ""
}

class GlobalFunctions:
    """全局函数"""
    def run_as_admin(self):
        """以管理员身份启动程序"""
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, __file__, None, 1
            )
            sys.exit()  # 退出当前非管理员进程

    def format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_filename(self, response):
        """获取文件名"""
        content_disposition = response.headers['content-disposition']
                            
        # 查找 filename= 或 filename*= 部分
        filename_match = re.findall(
        r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', 
            content_disposition, 
            flags=re.IGNORECASE
        )
                            
        if filename_match:
            # 取最后一个匹配（通常是最准确的）
            filename = unquote(filename_match[-1])
            # 清理可能的引号
            filename = filename.strip('"\'')

        return filename
    
    def get_total_size(self, response):
        """获取文件大小"""
        return int(response.headers.get('Content-Length', '0'))

    def download_from_server(self, filename):
        """从PMCL服务器下载"""
        with requests.get(f"https://pmcldownloadserver.dpdns.org/{filename}", stream=True, timeout=10) as response:
            response.raise_for_status()

            downloaded = 0
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded += len(chunk)
                    f.write(chunk)
    
    def check_update(self, from_help):
        """检查更新"""
        try:
            # 获取最新版本
            with requests.get("https://pmcldownloadserver.dpdns.org/latest_version_BE.json", timeout=10) as response:
                response.raise_for_status()
                check_update = response.text
            
            current_version = '1.0.2.0'
            have_later_version = False

            # 获取更新日志
            patch_notes = json.loads(check_update).get('patch_notes', '')
            
            # 一级一级版本号比对
            for i, version_name in enumerate(json.loads(check_update).get('latest_version', '0')):
                if i % 2 == 0:
                    if int(version_name) > int(current_version[i]):
                        have_later_version = True

            # 如果存在更新版本，下载它
            if have_later_version:
                version = json.loads(check_update).get('latest_version')
                if input(f"存在新版本：{version}，更新内容：{patch_notes}，是否更新？（y/n）（默认：y）") != 'n':
                    with requests.get("https://pmcldownloadserver.dpdns.org/PMCL_BE_CLI.exe", stream=True, timeout=10) as response:    
                        response.raise_for_status()
                        # 获取文件大小
                        total_size = int(response.headers.get('Content-Length', '0'))
                        
                        downloaded = 0
                        with open('update.exe', 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                downloaded += len(chunk)
                                f.write(chunk)
                                print(f"\033[2K \r{self.gf.format_file_size(downloaded)}/{self.gf.format_file_size(total_size)} {downloaded / total_size * 100:.2f}%", end='')

                    # 下载完成后继续更新过程
                    self.install_update()
                        
            elif from_help:
                print("\n已是最新版本")
        except Exception as e:
            print(f"检查或更新新版本失败：{e}")

    def install_update(self):
        """执行更新"""
        with open('updater.bat', 'w') as f:
            f.write("""
@echo off
setlocal
                            
echo 正在更新启动器……

:loop
tasklist /fi "imagename eq PMCL_BE_CLI.exe" /fo csv 2>nul | find /i "PMCL_BE_CLI.exe" >nul
if not errorlevel 1 (
    echo 等待启动器关闭……
    timeout /t 1 /nobreak >nul
    goto loop
)

del /q PMCL_BE_CLI.exe
move /y update.exe PMCL_BE_CLI.exe >nul

start PMCL_BE_CLI.exe

del /q updater.bat >nul
""")
        os.startfile('updater.bat')
        sys.exit()


class Download:
    def __init__(self):
        # 初始化全局函数
        self.gf = GlobalFunctions()
    def download_minecraft(self):
        """下载Minecraft"""
        try:
            selected_version = self.select_minecraft_versions()

            print(f"已选择：{selected_version['ID']}\n")
            print("请选择下载源：")
            print("1.日本节点")
            print("2.美国节点")
            print("3.中国节点")

            # 选择下载源
            sources = ['jp', 'us', 'cn']
            source = int(input("请输入数字："))
            print()

            # 发送GET请求，stream=True启用流式模式
            with requests.get(f"https://dl.mcappx.com/be-{selected_version['ID'].replace('.', '-')}-x64-{sources[source - 1]}", stream=True, timeout=10) as response:
                response.raise_for_status()  # 检查请求是否成功

                # 获取文件名和大小
                filename = self.gf.get_filename(response)
                total_size = self.gf.get_total_size(response)
                    
                downloaded = 0
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        downloaded += len(chunk)
                        f.write(chunk)  # 分块写入文件
                        print(f"\033[2K \r{self.gf.format_file_size(downloaded)}/{self.gf.format_file_size(total_size)} {downloaded / total_size * 100:.2f}%", end='')

            print("\n正在安装Minecraft……")
            if selected_version['BuildType'] == 'GDK':
                # 循环执行直到程序正常退出
                result = subprocess.run([filename])
                while result.returncode != 0:
                    if input("检测到程序没有正常退出，请问是否再次运行？（y/n）（默认：y）") != 'n':
                        result = subprocess.run([filename])
                    else:
                        break
                if input("是否清理安装包？（y/n）（默认：y）") != 'n':
                    os.remove(filename)
            else:
                print("检测到安装包类型为UWP，请问是否开启多版本共存模式？（y/n）（默认：n）")
                if input("请输入操作：") == 'y':
                    self.coexistence_UWP(filename) # UWP共存
                else:
                    result = subprocess.run(['cmd', '/c', filename])
                    while result.returncode != 0:
                        if input("检测到程序没有正常退出，请问是否再次运行？（y/n）（默认：y）") != 'n':
                            result = subprocess.run([filename])
                        else:
                            break
                if input("是否清理安装包？（y/n）（默认：y）") != 'n':
                    os.remove(filename)
            print(f"Minecraft {selected_version['ID']} 安装成功！")

        # 错误处理
        except requests.Timeout:
            print("下载Minecraft时连接超时。")
        except requests.HTTPError as e:
            print(f"下载Minecraft时HTTP错误：{e}")
        except Exception as e:
            print(f"下载Minecraft错误：{e}")
    
    def coexistence_UWP(self, filename):
        try:
            # 需要管理员
            if not ctypes.windll.shell32.IsUserAnAdmin():
                with open('incomplete_operation.txt', 'w') as f:
                    f.write(f'uwp_coexistence|{filename}')
                self.gf.run_as_admin()
            else:
                if os.path.exists('incomplete_operation.txt'):
                    os.remove('incomplete_operation.txt')
            # 输入包名
            package_name = 'Microsoft.MinecraftUWP' + input("请输入包名（只能包含字母和数字）：Microsoft.MinecraftUWP")
            
            # 解压文件
            with zipfile.ZipFile(filename, 'r') as zipf:
                print("解压文件中……")

                file_dir = os.path.join(os.path.abspath(''), os.path.splitext(filename)[0])
                total_files = len(zipf.namelist())
                extracted_files = 0

                for file in zipf.namelist():
                    zipf.extract(file, file_dir)
                    extracted_files += 1
                    print(f"\033[2K \r{extracted_files}/{total_files} {extracted_files / total_files * 100:.2f}%", end='')
            
            # 删除一些文件（文件夹）
            os.remove(os.path.join(file_dir, '[Content_Types].xml'))
            os.remove(os.path.join(file_dir, 'AppxSignature.p7x'))
            shutil.rmtree(os.path.join(file_dir, 'AppxMetadata'))

            # 替换包名
            with open(os.path.join(file_dir, 'AppxManifest.xml'), 'r', encoding='utf-8') as f:
                manifest = f.read()
            with open(os.path.join(file_dir, 'AppxManifest.xml'), 'w', encoding='utf-8') as f:
                f.write(manifest.replace('Microsoft.MinecraftUWP', package_name))
            
            # 修改注册表，启用开发人员模式
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"

            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            key.Close()

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, 'AllowDevelopmentWithoutDevLicense', 0, winreg.REG_DWORD, 1)
            
            # 安装Minecraft
            subprocess.call(['powershell', '/c', 'Add-AppxPackage', '-Register', os.path.join(file_dir, 'AppxManifest.xml')])

            # 恢复修改的注册表项
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, 'AllowDevelopmentWithoutDevLicense', 0, winreg.REG_DWORD, 0)
            print("\nUWP共存版安装成功！")
        # 错误处理
        except Exception as e:
            print(f"执行UWP共存错误：{e}")
    
    def select_minecraft_versions(self):
        """加载并选择Minecraft版本"""
        try:
            # 获取数据
            response = requests.get("https://data.mcappx.com/v2/bedrock.json")
            response.raise_for_status()
            response.encoding = 'utf-8'

            versions_json = json.loads(response.text)['From_mcappx.com']
            versions_keys = list(reversed(versions_json))

            for version in enumerate(versions_keys):
                print(f"{version[0] + 1}. {version[1]} （版本类型：{versions_json[version[1]]['Type']}，安装包类型：{versions_json[version[1]]['BuildType']}）")
                # 以20个为单位显示
                if (version[0] + 1) % 20 == 0:
                    try:
                        num = int(input("---按回车显示更多，或输入数字选择版本--- "))
                        return versions_json[str(versions_keys[num - 1])]
                    except:
                        continue
            else:
                num = int(input("按回车显示更多，请输入数字选择版本："))
                return versions_json[str(versions_keys[num - 1])]
        # 错误处理
        except requests.Timeout:
            print("下载Minecraft时连接超时。")
        except requests.HTTPError as e:
            print(f"加载列表时HTTP错误：{e}")
        except Exception as e:
            print(f"加载列表错误：{e}")

class Launch:
    def __init__(self):
        self.gf = GlobalFunctions() # 初始化全局函数
        self.manager = deployment.PackageManager() # 初始化包管理器
    
    def find_application(self, app_name):
        """根据应用名称查找应用。返回 AppListEntry 对象，如果没找到则返回 None。"""
        packages = self.manager.find_packages()
        
        minecraft_list = []

        for package in packages:
            # 获取包中的应用列表
            app_list_entries = package.get_app_list_entries()
            for app_entry in app_list_entries:
                # 如果应用显示名称包含搜索的关键词（不区分大小写）
                if app_name.lower() in app_entry.display_info.display_name.lower():
                    version_obj = package.id.version
                    package_family_name = package.id.family_name
                    minecraft_list.append([app_entry, f"{version_obj.major}.{version_obj.minor}.{version_obj.build}.{version_obj.revision}", package_family_name])
        
        if not minecraft_list:
            print(f"未找到Minecraft (UWP)")
            return None

        print("请选择要启动的Minecraft版本：")
        for i in enumerate(minecraft_list):
            print(f"{i[0] + 1}. {i[1][1]}")
        version = int(input("请输入数字："))
        return (minecraft_list[version - 1][0], minecraft_list[version - 1][2])
    
    async def launch_application_async(self, app_entry, package_family_name):
        """异步启动给定的 AppListEntry。"""
        try:
            if settings['EditorHint']:
                # 使用Launcher启动URI
                uri = foundation.Uri("minecraft://?Editor=true" if input("是否启动编辑器模式？（y/n）（默认：n）") == 'y' else "minecraft://")
            else:
                uri = foundation.Uri("minecraft://")

            # 创建启动选项
            options = ws.LauncherOptions()
            if package_family_name:
                options.target_application_package_family_name = package_family_name

            # 启动应用
            result = await ws.Launcher.launch_uri_async(uri, options)
            if result:
                print("Minecraft启动成功")
            else:
                result = await app_entry.launch_async()
                if result:
                    print("Minecraft启动成功")
                else:
                    print(f"Minecraft启动可能未成功（返回值：{result}）")
            return result
        except Exception as e:
            print(f"启动Minecraft时发生异常: {e}")
            return False
    
    def launch_application(self):
        """同步方法：查找并启动指定名称的应用。"""
        # 查找应用
        app_entry = self.find_application("Minecraft")
        if app_entry is None:
            return False
        
        # 启动应用
        print(f"正在启动Minecraft...")
        
        # 由于 launch_async 是异步的，需要在同步代码中运行它
        try:
            # 获取当前的事件循环，如果没有则创建新的
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 运行异步启动方法
        launch_result = loop.run_until_complete(self.launch_application_async(app_entry[0], app_entry[1]))
        return launch_result

    def launch(self, admin = False):
        try:
            global settings
            def launch_admin():
                # 使用管理员启动UWP
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    with open('incomplete_operation.txt', 'w') as f:
                        f.write('launch_uwp')
                    with open('pmcl_be_settings.json', 'w') as f:
                        json.dump(settings, f)
                    self.gf.run_as_admin()
                else:
                    if os.path.exists('incomplete_operation.txt'):
                        os.remove('incomplete_operation.txt')
                    self.launch_application()
            if admin:
                launch_admin()
                return

            # 启动Minecraft
            print("请输入要启动的版本类型：")
            print("1.UWP")
            print("2.GDK")
            if input("请输入数字：") == '1':
                if settings['UWPUnlock']:
                    if input("是否要使用解锁工具？（y/n）（默认：n）") == 'y':
                        if not os.path.exists('MinecraftUnlock++.exe'):
                            print("正在下载解锁工具……")
                            self.gf.download_from_server('MinecraftUnlock++.exe')

                        os.startfile('MinecraftUnlock++.exe')
                    settings['UWPUnlock'] = False
                launch_admin()
            else:
                print("\n缓存的路径：")

                if settings['GDKDir']:
                    self.cached_dirs = settings['GDKDir'].split('|')

                    # 去除空数据
                    for i in enumerate(self.cached_dirs):
                        if i[1] == '':
                            self.cached_dirs.pop(i[0])
                    
                    for dir in enumerate(self.cached_dirs):
                        print(f"{dir[0] + 1}. {dir[1]}")
                
                print("\n0.添加目录")
                if settings['GDKDir']:
                    print("-1.删除目录")
                operation = int(input("请输入数字："))

                if operation == 0:
                    # 添加目录
                    minecraft_dir = input("请输入Minecraft可执行文件目录，输入0打开图形化选择界面：")
                    if minecraft_dir == '0':
                        minecraft_dir = filedialog.askopenfilename(title="请选择Minecraft可执行文件目录", filetypes=[("Minecraft可执行文件", 'Minecraft.Windows.exe'), ("可执行文件", '*.exe'), ("所有文件", '*.*')])
                    settings['GDKDir'] += f'|{minecraft_dir}'

                elif operation == -1:
                    # 删除目录
                    dir = int(input("请输入想要删除的目录（数字）："))
                    settings['GDKDir'] = settings['GDKDir'].replace(f"|{self.cached_dirs[dir - 1]}", '')
                
                else:
                    if settings['EditorHint']:
                        arg = "minecraft://?Editor=true" if input("是否启动编辑器模式？（y/n）（默认：n）") == 'y' else ""
                    else:
                        arg = ""
                    if settings['GDKUnlock']:
                        if input("是否使用解锁工具？（y/n）（默认：n）") == 'y':
                            if not os.path.exists("injector.exe"):
                                # 加载解锁工具
                                print("正在下载解锁工具……")
                                self.gf.download_from_server('injector.exe')
                                
                                self.gf.download_from_server('MCpatcher2.dll')
                            
                            # 在另一个线程中启动解锁工具（不然会阻塞）
                            patcher_thread = threading.Thread(target=lambda: subprocess.call(['injector.exe']))
                            patcher_thread.daemon = True
                            patcher_thread.start()

                        subprocess.call([self.cached_dirs[operation - 1], arg])

            with open('pmcl_be_settings.json', 'w') as f:
                json.dump(settings, f)
        
        # 错误处理
        except requests.Timeout:
            print("下载破解工具时超时。")
        except requests.HTTPError as e:
            print(f"下载破解工具时HTTP错误：{e}")
        except Exception as e:
            print(f"启动MC失败：{e}")

class PMCLBEMain:
    def __init__(self):
        try:
            self.gf = GlobalFunctions()
            download = Download()
            launch = Launch()

            # 加载设置
            self.load_settings()

            # 如果有未完成的操作，继续执行
            if os.path.exists('incomplete_operation.txt'):
                with open('incomplete_operation.txt', 'r') as f:
                    operation = f.read()
                if 'uwp_coexistence' in operation:
                    download.coexistence_UWP(operation.split('|')[1])
                elif 'launch_uwp' in operation:
                    launch.launch(True)

            print("\n请选择操作：")
            print("1.安装Minecraft")
            print("2.启动Minecraft")
            print("3.设置")
            print("4.帮助")
            print("5.访问mcappx网站")
            print("0.退出程序")

            operation = int(input("请输入数字："))
            print()

            if operation == 1:
                download.download_minecraft()
            elif operation == 2:
                launch.launch()
            elif operation == 3:
                self.settings()
            elif operation == 4:
                self.help()
            elif operation == 5:
                webbrowser.open("mcappx.com")
            elif operation == 0:
                sys.exit()
        except Exception as e:
            print(f"主程序错误：{e}\n")

    def settings(self):
        """设置"""
        try:
            # 加载设置
            self.load_settings()

            print("设置")
            print(f"1.UWP使用解锁工具提示：{settings['UWPUnlock']}")
            print(f"2.GDK使用解锁工具提示：{settings['GDKUnlock']}")
            print(f"3.启动编辑器模式提示：{settings['EditorHint']}")
            print("0.不保存")
            print("\n（选择选项后会自动保存）")

            self.UWPUnlock = None
            self.GDKUnlock = None
            self.EditorHint = None

            operation = int(input("请输入数字："))
            if operation == 1:
                self.UWPUnlock = False
                if input("请输入选项（y/n）（默认：n）") == 'y':
                    self.UWPUnlock = True
            elif operation == 2:
                self.GDKUnlock = False
                if input("请输入选项（y/n）（默认：n）") == 'y':
                    self.GDKUnlock = True
            elif operation == 3:
                self.EditorHint = False
                if input("请输入选项（y/n）（默认：n）") == 'y':
                    self.EditorHint = True
            if operation != 0:
                self.save_settings()
        
        # 错误处理
        except Exception as e:
            print(f"设置错误：{e}")

    def load_settings(self):
        """尝试从配置文件获取设置"""
        try:
            global settings
            if os.path.exists('pmcl_be_settings.json'):
                with open('pmcl_be_settings.json', 'r') as f:
                    settings = json.load(f)
        # 错误处理
        except Exception as e:
            print(f"加载设置错误：{e}")

    def save_settings(self):
        """保存设置"""
        try:
            global settings
            settings = {
                "UWPUnlock": self.UWPUnlock if self.UWPUnlock is not None else settings['UWPUnlock'],
                "GDKUnlock": self.GDKUnlock if self.GDKUnlock is not None else settings['GDKUnlock'],
                "EditorHint": self.EditorHint if self.EditorHint is not None else settings['EditorHint'],
                "GDKDir": settings['GDKDir']
            }
            with open('pmcl_be_settings.json', 'w') as f:
                json.dump(settings, f)
        # 错误处理
        except Exception as e:
            print(f"保存设置错误：{e}")
    
    def help(self):
        """帮助"""
        try:
            print("请选择操作：")
            print("1.关于")
            print("2.支持与反馈")
            print("3.打开网站")
            print("4.检查更新")
            operation = int(input("请输入数字："))

            if operation == 1:
                print("\n关于\nPython Minecraft Launcher: Bedrock Edition (Command Line) (PMCL_BE_CLI)\n版本 1.0.2\nBilibili 七星五彩 Gitcode & Github Dilideguazi 版权所有。\n本软件遵循GPLv3协议，请严格遵守本协议使用。\n特别鸣谢：mcappx.com 提供下载API 自信的Eric（B站） 提供MinecraftUnlock++")
            elif operation == 2:
                print("\n若有意见，请去Gitcode或Github！")
            elif operation == 3:
                print("\n请选择网站：")
                print("1.B站主页")
                print("2.Gitcode")
                print("3.Github")
                print("4.Github镜像站")
                website = int(input("请输入数字："))
                websites = ["https://space.bilibili.com/1191376859", "https://gitcode.com/Dilideguazi/Python_Minecraft_Launcher_Bedrock_Edition_Command_Line", "https://github.com/Dilideguazi/Python_Minecraft_Launcher_Bedrock_Edition_Command_Line", "https://dgithub.xyz/Dilideguazi/Python_Minecraft_Launcher_Bedrock_Edition_Command_Line"]
                
                webbrowser.open(websites[website - 1])
            elif operation == 4:
                self.gf.check_update(True)

        # 错误处理
        except Exception as e:
            print(f"帮助错误：{e}")

if __name__ == '__main__':
    if not os.path.exists('incomplete_operation.txt'):
        # 检查更新
        GlobalFunctions().check_update(False)
    while True:
        PMCLBEMain()
