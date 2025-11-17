#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shell智能助手 - 通过自然语言使用Linux Shell
基于华东师范大学ChatECNU API实现

功能:
- 通过自然语言描述自动生成Shell命令
- 支持命令执行和结果实时展示
- 命令历史记录和补全功能
- 安全检查和错误处理
- 跨平台兼容性
"""

import os
import sys
import json
import requests
import subprocess
import threading
try:
    import pyfiglet
    has_figlet = True
except ImportError:
    has_figlet = False

# 尝试导入PIL库用于处理图片
try:
    from PIL import Image, ImageEnhance
    has_pil = True
except ImportError:
    has_pil = False
# 尝试导入readline模块，Windows可能不支持
try:
    import readline  # 提供命令行补全和历史记录功能
except ImportError:
    # Windows系统使用pyreadline作为替代
    try:
        import pyreadline as readline
    except ImportError:
        readline = None  # 没有readline模块时，补全功能不可用
from datetime import datetime
import time
import signal
import shutil

# 尝试导入term_image库
try:
    from term_image.image import from_file
    has_term_image = True
except ImportError:
    has_term_image = False

class ECNUShellAssistant:
    def __init__(self):
        # 初始化配置
        self.config = self._load_config()
        
        # 初始化多模型支持
        self._init_model_manager()
       # 设置默认模型
        # 设置当前模型为GLM-4.6模型（默认使用魔搭社区的大模型）
        default_model = "GLM-4.6"
        self.model = default_model
        self._set_current_model(default_model)
        
        # 初始化历史记录和其他属性
        self.history = []  # 保存对话历史
        self.command_history = []  # 保存执行过的shell命令
        self.max_history_size = self.config.get("max_history_size", 100)  # 最大历史记录数
        
        # 确保有默认值的显示配置选项
        if "show_ascii_banner" not in self.config:
            self.config["show_ascii_banner"] = True  # 是否显示ASCII文本标识
        if "badge_image_path" not in self.config:
            self.config["badge_image_path"] = None  # 校徽图片路径（预留接口）
        if "use_colored_output" not in self.config:
            self.config["use_colored_output"] = True  # 是否使用彩色输出
            
        self.setup_prompt()
        self._setup_readline()  # 设置命令行补全
    
    def _init_model_manager(self):
        """初始化模型管理器"""
        # 定义支持的模型提供商和模型
        self.model_providers = {
            # Qwen/Qwen3-32B模型 (默认，使用魔搭社区)
            "Qwen/Qwen3-32B": {
                "provider": "modelscope",
                "api_base_url": "https://api-inference.modelscope.cn/v1",
                "api_key_env": "MODEL_SCOPE_API",
                "endpoint": "/chat/completions"
            },
            # GLM-4.6模型 (可选)
            "GLM-4.6": {
                "provider": "modelscope",
                "api_base_url": "https://api-inference.modelscope.cn/v1",
                "api_key_env": "MODEL_SCOPE_API",
                "endpoint": "/chat/completions",
                "model_id": "ZhipuAI/GLM-4.6"
            },
            # ECNU Chat模型 (可选)
            "ecnu-plus": {
                "provider": "ecnu",
                "api_base_url": "https://chat.ecnu.edu.cn/open/api/v1",
                "api_key_env": "ECNU_API_KEY",
                "endpoint": "/chat/completions"
            },
            "ecnu-max": {
                "provider": "ecnu",
                "api_base_url": "https://chat.ecnu.edu.cn/open/api/v1",
                "api_key_env": "ECNU_API_KEY",
                "endpoint": "/chat/completions"
            },
            "ChatECNU": {
                "provider": "ecnu",
                "api_base_url": "https://chat.ecnu.edu.cn/open/api/v1",
                "api_key_env": "ECNU_API_KEY",
                "endpoint": "/chat/completions"
            }
        }
        
        # 获取可用模型列表
        self.available_models = list(self.model_providers.keys())
        
        # 初始化当前API设置
        self.api_base_url = self.config.get("api_base_url", "https://chat.ecnu.edu.cn/open/api/v1")
        self.api_key = self._get_api_key()
        
        # 确保API密钥有效，并设置请求头
        if not self.api_key:
            print("警告: 未能获取到有效的API密钥")
        
        # 初始化速率限制跟踪
        self.rate_limit = {
            'rpm': self.config.get('rate_limit_rpm', 10),  # 每分钟请求限制
            'rph': self.config.get('rate_limit_rph', 60),  # 每小时请求限制
            'rpd': self.config.get('rate_limit_rpd', 100), # 每天请求限制
            'requests': []  # 存储请求时间戳
        }
        
        # 初始化速率限制控制标志（默认开启）
        self.rate_limit_enabled = True
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
    
    def _set_current_model(self, model_name):
        """设置当前使用的模型，并提供详细的配置反馈"""
        # 设置颜色输出
        if self._supports_color():
            YELLOW = '\033[93m'
            GREEN = '\033[92m'
            RED = '\033[91m'
            RESET = '\033[0m'
        else:
            YELLOW = GREEN = RED = RESET = ""
            
        
        
        if model_name not in self.model_providers:
            print(f"{RED}错误: 不支持的模型 '{model_name}'{RESET}")
            print(f"{YELLOW}支持的模型列表: {', '.join(self.model_providers.keys())}{RESET}")
            print(f"{YELLOW}您可以使用 'set model [model_name]' 命令切换模型{RESET}")
            return False
        
        # 获取模型配置
        model_config = self.model_providers[model_name]
        api_key_env = model_config["api_key_env"]
        provider = model_config["provider"]
        
       
        
        # 更新API基础URL
        self.api_base_url = model_config["api_base_url"]
        
        # 从环境变量获取API密钥
        self.api_key = os.environ.get(api_key_env, "")

        api_source = "未找到"
        
        if self.api_key:
            api_source = f"环境变量 ({api_key_env})"
        
        # 如果没有设置环境变量，尝试从配置文件获取
        if not self.api_key and "api_keys" in self.config:
            # 尝试使用provider或api_key_env作为键获取
            self.api_key = self.config["api_keys"].get(provider, "")
            if not self.api_key:
                self.api_key = self.config["api_keys"].get(api_key_env, "")
            if self.api_key:
                api_source = "配置文件"
    
        
        # 更新请求头
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        
        # 更新当前模型
        self.model = model_name
        
        # 打印详细的模型切换信息
        print(f"{GREEN}模型已切换至: {model_name}{RESET}")
        print(f"{YELLOW}提供商: {provider}{RESET}")
        print(f"{YELLOW}API端点: {self.api_base_url}{RESET}")
        
        # 检查API密钥状态并提供友好提示
        if not self.api_key:
            print(f"{RED}警告: 未找到有效的API密钥！{RESET}")
            print(f"{YELLOW}请通过以下方式之一配置API密钥:{RESET}")
            print(f"  1. 设置环境变量: export {api_key_env}=your_api_key_here")
            print(f"  2. 在配置文件中添加: ")
            print(f"     {{\n       \"api_keys\": {{\n         \"{api_key_env}\": \"your_api_key_here\"\n       }}\n     }}")
            print(f"{YELLOW}注意: 没有API密钥时，模型功能将无法正常工作{RESET}")
        else:
            print(f"{GREEN}API密钥状态: 已配置 (来源: {api_source}){RESET}")
        
        return True
    
    def _get_api_key(self):
        """从环境变量或配置文件获取API密钥"""
        # 尝试获取当前模型对应的API密钥
        if hasattr(self, 'model') and self.model in self.model_providers:
            model_config = self.model_providers[self.model]
            api_key_env = model_config["api_key_env"]
            api_key = os.environ.get(api_key_env)
            
            # 对于GLM-4.6模型，特别检查MODEL_SCOPE_API环境变量
            if self.model == "GLM-4.6" and not api_key:
                api_key = os.environ.get("MODEL_SCOPE_API")
        else:
            # 如果模型不在预定义列表中或尚未设置，使用默认环境变量
            # 优先尝试GLM-4.6的环境变量
            api_key = os.environ.get("MODEL_SCOPE_API")
            # 如果没有，回退到ECNU的环境变量
            if not api_key:
                api_key = os.environ.get("ECNU_API_KEY")
        
        # 2. 如果环境变量没有，尝试从配置中获取
        if not api_key:
            api_key = self.config.get("api_key")
        
        # 3. 如果配置中没有，尝试从旧的API密钥文件读取
        if not api_key:
            config_path = os.path.expanduser("~/.ecnu_api_key")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        api_key = f.read().strip()
                    # 迁移到新的配置文件
                    self.config["api_key"] = api_key
                    self._save_config()
                except Exception as e:
                    print(f"读取API密钥文件错误: {e}")
        
        # 清理API密钥，移除可能的空格和换行符
        if api_key:
            api_key = api_key.strip()
        
        # 4. 如果还是没有API密钥，提示用户输入
        if not api_key:
            print(f"\n需要{self.model}模型的API密钥才能使用该助手")
            print(f"您可以通过设置环境变量 {self.model_providers[self.model]['api_key_env']} 来配置API密钥")
            try:
                api_key = input(f"请输入您的{self.model} API密钥: ")
                # 询问是否保存API密钥
                save = input("是否保存API密钥？(y/n): ")
                if save.lower() == 'y':
                    self.config["api_key"] = api_key
                    self._save_config()
                    print("API密钥已保存到配置文件")
            except KeyboardInterrupt:
                print("\n操作已取消")
                sys.exit(1)
        
        return api_key
    
    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.expanduser("~/.ecnu_shell_config.json")
        default_config = {
            "api_base_url": "https://api-inference.modelscope.cn/v1",
            "model": "Qwen/Qwen3-32B",
            "max_history_size": 100,
            "command_timeout": 60,
            "temperature": 0.1,
            "top_p": 0.7,
            "show_background_image": True,
            "background_image_opacity": 0.1,
            "quiet_mode": False
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置和用户配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"加载配置文件错误: {e}")
                return default_config
        
        # 如果配置文件不存在，返回默认配置
        return default_config
    
    def _save_config(self):
        """保存配置到文件"""
        config_path = os.path.expanduser("~/.ecnu_shell_config.json")
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            # 保存配置，不保存API密钥到日志
            config_to_save = self.config.copy()
            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            # 设置文件权限为仅用户可读可写
            if os.name != 'nt':  # Windows不支持chmod
                os.chmod(config_path, 0o600)
        except Exception as e:
            print(f"保存配置文件错误: {e}")
    
    def _setup_readline(self):
        """设置命令行补全和历史记录"""
        # 检查readline模块是否可用
        if readline is None:
            return
            
        try:
            # 设置历史记录文件
            hist_file = os.path.expanduser("~/.ecnu_shell_input_history")
            
            # 读取历史记录
            if os.path.exists(hist_file):
                try:
                    readline.read_history_file(hist_file)
                    # 设置历史记录长度
                    readline.set_history_length(1000)
                except:
                    # 无法读取历史记录时静默处理
                    pass
            
            # 设置补全函数
            def completer(text, state):
                try:
                    # 合并所有可能的补全选项
                    options = []
                    
                    # 添加命令历史补全
                    options.extend([cmd for cmd in self.command_history if cmd.startswith(text)])
                    
                    # 添加内置命令补全
                    builtin_cmds = ['help', 'exit', 'quit', 'clear', 'cls', 'history', 'config']
                    options.extend([cmd for cmd in builtin_cmds if cmd.startswith(text)])
                    
                    # 添加当前目录下的文件和目录补全
                    try:
                        import glob
                        # 获取输入中最后一个空格后的部分作为路径前缀
                        if ' ' in text:
                            path_prefix = text.split(' ')[-1]
                            base_dir = os.path.dirname(path_prefix) or '.'
                            prefix = os.path.basename(path_prefix)
                            
                            # 获取匹配的文件和目录
                            try:
                                matches = glob.glob(os.path.join(base_dir, prefix + '*'))
                                
                                # 添加补全选项，根据操作系统使用正确的分隔符
                                for match in matches:
                                    if os.path.isdir(match):
                                        # 在Windows上使用\，在Unix上使用/
                                        sep = '\\' if os.name == 'nt' else '/'
                                        options.append(match + sep)
                                    else:
                                        options.append(match)
                            except:
                                pass
                        else:
                            # 简单的文件名补全
                            try:
                                matches = glob.glob(text + '*')
                                for match in matches:
                                    if os.path.isdir(match):
                                        sep = '\\' if os.name == 'nt' else '/'
                                        options.append(match + sep)
                                    else:
                                        options.append(match)
                            except:
                                pass
                    except:
                        pass
                    
                    # 去重并排序
                    options = sorted(list(set(options)))
                    
                    # 返回指定索引的补全选项
                    if state < len(options):
                        return options[state]
                    else:
                        return None
                except:
                    # 补全出错时返回None
                    return None
            
            # 设置补全器
            readline.set_completer(completer)
            readline.set_completer_delims(' \t\n`~!@#$%^&*()-=+[{]}\\|;:\'",<>?')
            
            # 启用Tab键补全
            try:
                if sys.platform == 'darwin':  # macOS
                    readline.parse_and_bind('bind ^I rl_complete')
                elif os.name == 'nt':  # Windows
                    # Windows下的pyreadline配置
                    readline.parse_and_bind('tab: complete')
                else:  # Linux
                    readline.parse_and_bind('tab: complete')
            except:
                # 绑定失败时静默处理
                pass
            
            # 保存历史记录的函数
            def save_history():
                try:
                    # 确保历史目录存在
                    os.makedirs(os.path.dirname(hist_file), exist_ok=True)
                    readline.write_history_file(hist_file)
                except:
                    pass
            
            # 注册退出时保存历史记录
            try:
                import atexit
                atexit.register(save_history)
            except:
                pass
            
        except:
            # 整体设置出错时静默处理，不影响主程序
            pass
    
    def setup_prompt(self):
        """设置系统提示词，指导模型生成Shell命令"""
        # 根据操作系统调整提示词
        os_type = "Windows" if os.name == 'nt' else "Linux/Unix"
        
        system_prompt = {
            "role": "system",
            "content": f"你是一个专业的Shell命令转换助手。用户会用自然语言描述他们想要执行的操作，请将其转换为正确、高效、安全的{os_type} Shell命令。\n"
                      "请严格遵循以下规则：\n"
                      "1. 只输出要执行的Shell命令，不要有任何额外的解释、说明文字或格式标记\n"
                      "2. 确保命令是安全的，避免使用可能破坏系统的操作（如rm -rf、格式化等）\n"
                      "3. 优先使用常见、通用的命令，确保在目标操作系统上可用\n"
                      "4. 对于查看文件内容，根据文件大小选择合适的命令\n"
                      "5. 对于复杂操作，使用管道和重定向等Shell特性构建高效命令\n"
                      "6. 为了安全，添加适当的选项（如rm命令添加-i选项）\n"
                      "7. 如果用户请求不明确，生成一个最接近的通用命令\n"
                      "8. 输出必须是单个、完整、可直接执行的Shell命令"
        }
        self.history.append(system_prompt)
    
    def _show_loading_animation(self, stop_event, message="正在处理"):
        """显示加载动画"""
        # 动画字符集合
        animation = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        while not stop_event.is_set():
            sys.stdout.write(f"\r{message} {animation[i % len(animation)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        # 清除动画行
        sys.stdout.write("\r" + " " * (len(message) + 3) + "\r")
        sys.stdout.flush()
        
    def natural_language_to_shell(self, natural_language):
        """将自然语言转换为Shell命令"""
        try:
            # 导入Anthropic客户端库（根据用户提供的补充信息）
            try:
                import anthropic
                has_anthropic = True
            except ImportError:
                print("错误: 未安装Anthropic客户端库。请运行 pip install anthropic")
                return None
            
            # 预处理用户输入
            natural_language = natural_language.strip()
            if not natural_language:
                return None
                
            # 添加更明确的指令，指定目标操作系统
            os_type = "Windows" if os.name == 'nt' else "Linux/Unix"
            enhanced_input = f"在{os_type}系统上，将以下自然语言转换为Shell命令: {natural_language}\n请输出单个、完整、可执行的命令，不要其他内容。"
            
            # 添加用户消息到历史记录
            self.history.append({"role": "user", "content": enhanced_input})
            
            # 验证API密钥是否存在且有效
            
            if not self.api_key or len(self.api_key) < 10:
                print(f"错误: API密钥无效或为空。请确保已正确设置{self.model}模型的API密钥环境变量。")
                print(f"请设置对应的环境变量，例如:")
                if self.model.startswith("ecnu"):
                    print("$env:ECNU_API_KEY='您的API密钥'  # PowerShell")
                    print("export ECNU_API_KEY='您的API密钥'  # Linux/WSL")
                elif self.model.startswith("minimax"):
                    print("$env:MODEL_SCOPE_API='您的API密钥'  # PowerShell")
                    print("export MODEL_SCOPE_API='您的API密钥'  # Linux/WSL")
                return None
            
            # 检查速率限制
            if not self._check_rate_limit():
                # 增强的速率限制处理
                print("警告: 达到请求限制。请等待几秒后重试。")
                import time
                time.sleep(2)  # 强制等待2秒后再重试
                
                # 再次检查速率限制
                if not self._check_rate_limit():
                    print("错误: 仍然超出请求限制。请稍后再试。")
                    return None
            
            # 记录请求时间
            self._record_request()
            
            # 添加额外的安全延迟，避免触发速率限制
            import time
            time.sleep(1)  # 请求前的安全延迟
            
            # 根据模型提供商选择不同的API调用方式
            try:
                # 导入必要的模块
                import threading
                
                # 启动加载动画
                stop_event = threading.Event()
                animation_thread = threading.Thread(
                    target=self._show_loading_animation,
                    args=(stop_event, "正在转换自然语言到Shell命令")
                )
                animation_thread.daemon = True
                animation_thread.start()
                
                # 导入OpenAI库
                from openai import OpenAI
                
                # 获取当前模型的配置信息
                model_config = self.model_providers.get(self.model, {})
                provider = model_config.get('provider', 'modelscope')
                
                # 根据提供商初始化不同的客户端
                # 对于ECNU模型，使用ECNU API端点
                if provider == 'ecnu':
                    # 使用ChatECNU API端点
                    client = OpenAI(
                        base_url=model_config.get('api_base_url', 'https://chat.ecnu.edu.cn/open/api/v1'),
                        api_key=self.api_key  # ECNU API Key
                    )
                else:
                    # 对于ModelScope模型，使用ModelScope API端点
                    client = OpenAI(
                        base_url=model_config.get('api_base_url', 'https://api-inference.modelscope.cn/v1'),
                        api_key=self.api_key  # ModelScope Token
                    )
                
                # 准备消息格式
                messages = []
                
                # 提取并添加系统提示词
                system_prompt_found = False
                for msg in self.history:
                    if msg["role"] == "system":
                        messages.append({"role": "system", "content": msg["content"]})
                        system_prompt_found = True
                        break
                
                # 如果没有系统提示词，使用默认的
                if not system_prompt_found:
                    messages.append({
                        "role": "system", 
                        "content": "你是一个Shell命令转换助手，请将自然语言转换为准确的Shell命令。只返回命令，不要添加解释。"
                    })
                
                # 添加最新的用户消息
                user_messages = [msg for msg in self.history if msg["role"] == "user"]
                if user_messages:
                    # 添加最后一条用户消息
                    messages.append({"role": "user", "content": user_messages[-1]["content"]})
                else:
                    # 如果没有用户消息历史，使用当前输入
                    messages.append({"role": "user", "content": natural_language})
                
                # 获取模型配置
                model_config = self.model_providers.get(self.model, {})
                
                # 确定要使用的模型ID（优先使用配置中的model_id，如果没有则使用模型名称）
                model_id = model_config.get('model_id', self.model)
                
                # 简化请求参数
                request_params = {
                    'model': model_id,  # 使用正确的模型ID
                    'messages': messages,
                    'stream': False  # 只保留必要参数
                }
                
                # Qwen3-32B模型需要使用extra_body传递enable_thinking参数
                if self.model == 'Qwen/Qwen3-32B':
                    request_params['extra_body'] = {"enable_thinking": False}
                
                # 发送请求
                response = client.chat.completions.create(**request_params)
                
                # 解析响应
                if hasattr(response, 'choices') and response.choices:
                    choice = response.choices[0]
                    if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                        full_response = choice.message.content
                    else:
                        raise ValueError("响应中没有找到message或content")
                else:
                    raise ValueError("响应中没有choices字段")
                
                # 停止加载动画
                stop_event.set()
                animation_thread.join(timeout=0.2)  # 等待动画线程结束
                
                # 显示响应内容
                if not self.config.get("quiet_mode", False):
                    print(full_response, flush=True)
                    print()  # 换行
                
                # 清理命令，移除可能的格式标记或额外文本
                shell_command = self._clean_command(full_response)
                
                # 添加助手回复到历史记录
                self.history.append({"role": "assistant", "content": shell_command})
                
                # 限制历史记录大小
                if len(self.history) > self.max_history_size:
                    # 保留系统提示词，移除最旧的交互
                    system_prompt = self.history[0]  # 假设第一个始终是系统提示词
                    self.history = [system_prompt] + self.history[-self.max_history_size+1:]
                
                return shell_command
                
            except Exception as e:
                # 停止加载动画
                stop_event.set()
                animation_thread.join(timeout=0.2)  # 等待动画线程结束
                
                error_msg = f"API错误: {str(e)}"
                if not self.config.get("quiet_mode", False):
                    print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
                
                # 特殊处理速率限制错误
                if "429" in str(e) or "rate limit" in str(e).lower():
                    print("提示: 遇到速率限制。请等待10秒后再试。")
                    time.sleep(10)
                
                return None
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            if not self.config.get("quiet_mode", False):
                print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return None
        except requests.exceptions.ConnectionError:
            error_msg = "网络连接错误"
            if not self.config.get("quiet_mode", False):
                print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return None
        except requests.exceptions.HTTPError as http_err:
            # 特定错误码处理
            error_msg = ""
            if response.status_code == 401:
                error_msg = "认证失败，请检查您的API密钥是否正确"
            elif response.status_code == 429:
                error_msg = "请求过于频繁，请稍后再试"
            else:
                error_msg = f"HTTP错误: {http_err}"
            
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            self._log_error(f"API请求错误: {error_msg}")
            return None
        except Exception as e:
            error_msg = f"转换自然语言到Shell命令时出错: {e}"
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            self._log_error(f"转换错误: {str(e)}")
            # 尝试使用回退机制
            print("\n正在尝试使用本地回退机制生成命令...")
            shell_command = self._simple_command_fallback(natural_language)
            if shell_command:
                print(f"[回退模式] 生成的命令: {shell_command}")
                self.history.append({"role": "assistant", "content": shell_command})
                return shell_command
            return None
    
    def explain_shell_command(self, command):
        """
        助教模式2：解析Linux命令并输出语法以及预期结果
        """
        if not self.config.get("quiet_mode", False):
            print(f"正在解析命令: {command}")
        
        # 创建停止事件用于控制加载动画
        stop_event = threading.Event()
        
        # 启动加载动画线程
        loading_thread = threading.Thread(
            target=self._show_loading_animation,
            args=(stop_event, "解析命令中")
        )
        loading_thread.daemon = True
        loading_thread.start()
        
        try:
            # 准备解释提示
            explain_prompt = f"""
            请详细解释以下Linux命令的语法、参数含义和预期执行结果：
            {command}
            
            请按照以下格式输出：
            【命令】
            {command}
            【语法】
            命令的语法说明，包括各参数的作用和用法
            【参数解析】
            详细解释命令中每个参数的含义（如果有）
            【预期结果】
            命令执行后可能产生的输出和效果
            【注意事项】
            使用该命令时需要注意的事项（如权限要求等）
            """
            
            # 导入OpenAI库
            from openai import OpenAI
            
            # 获取当前模型的配置信息
            model_config = self.model_providers.get(self.model, {})
            provider = model_config.get('provider', 'modelscope')
            
            # 根据提供商初始化不同的客户端
            # 对于ECNU模型，使用ECNU API端点
            if provider == 'ecnu':
                # 使用ChatECNU API端点
                client = OpenAI(
                    base_url=model_config.get('api_base_url', 'https://chat.ecnu.edu.cn/open/api/v1'),
                    api_key=self.api_key  # ECNU API Key
                )
            else:
                # 对于ModelScope模型，使用ModelScope API端点
                client = OpenAI(
                    base_url=model_config.get('api_base_url', 'https://api-inference.modelscope.cn/v1'),
                    api_key=self.api_key  # ModelScope Token
                )
            
            # 获取模型配置
            model_config = self.model_providers.get(self.model, {})
            
            # 确定要使用的模型ID（优先使用配置中的model_id，如果没有则使用模型名称）
            current_model = model_config.get('model_id', self.model)
            
            # 准备请求参数
            request_params = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": "你是一位Linux教学助手，精通各种Linux命令及其用法。请详细解释Linux命令的语法、参数含义和预期执行结果，确保解释清晰易懂。"},
                    {"role": "user", "content": explain_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            }
            
            # Qwen3-32B模型需要使用extra_body传递enable_thinking参数
            if self.model == 'Qwen/Qwen3-32B':
                request_params["extra_body"] = {"enable_thinking": False}
            
            # 发送请求
            response = client.chat.completions.create(**request_params)
            
            # 停止加载动画
            stop_event.set()
            loading_thread.join(timeout=0.2)
            
            # 解析响应
            if hasattr(response, 'choices') and response.choices:
                explanation = response.choices[0].message.content
                print("\n" + explanation)
                return True
            else:
                raise ValueError("未能获取有效的命令解释响应")
                
        except Exception as e:
            # 停止加载动画
            stop_event.set()
            loading_thread.join(timeout=0.2)
            
            error_msg = f"解析命令失败: {str(e)}"
            if not self.config.get("quiet_mode", False):
                print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return False
            
    def explain_natural_language(self, natural_language):
        """
        助教模式1：将自然语言转换为Linux命令并提供语法解释
        """
        if not self.config.get("quiet_mode", False):
            print("正在生成Linux命令及解释...")
        
        # 创建停止事件用于控制加载动画
        stop_event = threading.Event()
        
        # 启动加载动画线程
        loading_thread = threading.Thread(
            target=self._show_loading_animation,
            args=(stop_event, "生成命令解释中")
        )
        loading_thread.daemon = True
        loading_thread.start()
        
        try:
            # 准备解释提示
            explain_prompt = f"""
            请将以下自然语言需求转换为Linux命令，并提供详细解释：
            {natural_language}
            
            请按照以下格式输出：
            【命令】
            具体的Linux命令
            【解释】
            对命令的详细解释，包括每个参数的作用、语法说明等
            【示例】
            命令在常见场景中的使用示例（如果适用）
            """
            
            # 导入OpenAI库
            from openai import OpenAI
            
            # 获取当前模型的配置信息
            model_config = self.model_providers.get(self.model, {})
            provider = model_config.get('provider', 'modelscope')
            
            # 根据提供商初始化不同的客户端
            # 对于ECNU模型，使用ECNU API端点
            if provider == 'ecnu':
                # 使用ChatECNU API端点
                client = OpenAI(
                    base_url=model_config.get('api_base_url', 'https://chat.ecnu.edu.cn/open/api/v1'),
                    api_key=self.api_key  # ECNU API Key
                )
            else:
                # 对于ModelScope模型，使用ModelScope API端点
                client = OpenAI(
                    base_url=model_config.get('api_base_url', 'https://api-inference.modelscope.cn/v1'),
                    api_key=self.api_key  # ModelScope Token
                )
            
            # 获取模型配置
            model_config = self.model_providers.get(self.model, {})
            
            # 确定要使用的模型ID（优先使用配置中的model_id，如果没有则使用模型名称）
            current_model = model_config.get('model_id', self.model)
            
            # 准备请求参数
            request_params = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": "你是一位Linux教学助手，精通各种Linux命令及其用法。请将自然语言转换为准确的Linux命令，并提供清晰易懂的解释。"},
                    {"role": "user", "content": explain_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            }
            
            # Qwen3-32B模型需要使用extra_body传递enable_thinking参数
            if self.model == 'Qwen/Qwen3-32B':
                request_params["extra_body"] = {"enable_thinking": False}
            
            # 发送请求
            response = client.chat.completions.create(**request_params)
            
            # 停止加载动画
            stop_event.set()
            loading_thread.join(timeout=0.2)
            
            # 解析响应
            if hasattr(response, 'choices') and response.choices:
                explanation = response.choices[0].message.content
                print("\n" + explanation)
                return True
            else:
                raise ValueError("未能获取有效的解释响应")
                
        except Exception as e:
            # 停止加载动画
            stop_event.set()
            loading_thread.join(timeout=0.2)
            
            error_msg = f"生成解释失败: {str(e)}"
            if not self.config.get("quiet_mode", False):
                print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return False
            
    def _simple_command_fallback(self, natural_language):
        """简单的命令生成回退机制，当API调用失败时使用"""
        # 转换为小写进行匹配
        natural_language = natural_language.lower()
        
        # 简单的命令映射
        command_map = {
            # 目录操作
            "列出文件": "dir",
            "ls": "dir",
            "显示当前目录": "cd",
            "pwd": "cd",
            "切换目录": "cd",
            "创建目录": "mkdir",
            "删除目录": "rmdir",
            # 文件操作
            "创建文件": "echo >",
            "查看文件": "type",
            "删除文件": "del",
            "复制文件": "copy",
            "移动文件": "move",
            # 系统信息
            "系统信息": "systeminfo",
            "ip地址": "ipconfig",
            "进程列表": "tasklist",
            # 其他常用命令
            "清屏": "cls",
            "退出": "exit"
        }
        
        # 查找匹配的命令
        for key, cmd in command_map.items():
            if key in natural_language:
                return cmd
        
        # 处理特殊情况
        if "hello" in natural_language or "你好" in natural_language:
            return "echo Hello, World!"
        elif "test" in natural_language:
            return "echo 测试命令执行成功"
        elif "list" in natural_language or "ls" in natural_language or "dir" in natural_language:
            return "dir"
        elif "cd" in natural_language or "切换目录" in natural_language or "目录" in natural_language:
            return "cd"
        elif "file" in natural_language or "文件" in natural_language:
            return "dir"
        elif "system" in natural_language or "系统" in natural_language:
            return "systeminfo"
        elif "exit" in natural_language or "退出" in natural_language or "quit" in natural_language:
            return "exit"
        elif "clear" in natural_language or "清屏" in natural_language:
            return "cls"
        # 默认响应
        return "echo 无法识别的命令。试试输入'列出文件'、'系统信息'或'你好'等简单命令。"
        
    def _clean_command(self, command):
        """清理生成的命令，移除不需要的格式标记和文本"""
        # 移除代码块标记
        command = command.strip()
        if command.startswith('```'):
            # 可能是 ```bash 或 ```shell 或 ```
            command = '\n'.join([line for line in command.split('\n')[1:] if not line.startswith('```')])
        
        # 移除可能的前缀如"命令: "或"bash: "
        prefixes = ['命令: ', 'bash: ', 'shell: ', '$ ']
        for prefix in prefixes:
            if command.startswith(prefix):
                command = command[len(prefix):]
                break
        
        # 移除多余的空格和换行符
        command = ' '.join(command.split())
        
        return command.strip()

    def execute_shell_command(self, command):
        """执行Shell命令并实时展示结果"""
        try:
            if not self.config.get("quiet_mode", False):
                print(f"执行: {command}")
            
            # 保存命令到历史记录
            self.command_history.append(command)
            
            # 从配置中获取超时时间
            timeout = self.config.get("command_timeout", 60)
            
            # 检测是否为sudo命令
            is_sudo_command = 'sudo' in command and not command.startswith('#')
            
            if is_sudo_command and os.name != 'nt':
                # 对于sudo命令，进行特殊处理以确保密码输入正常工作
                print("注意：此命令需要管理员权限，您可能需要输入密码。")
                print("密码输入时不会显示字符，这是正常的安全机制。")
                
                # 对于sudo命令，我们不捕获stdin，让其直接从终端读取
                # 但仍尝试捕获并显示stdout和stderr
                try:
                    # 使用os.system直接执行sudo命令，这样可以正常处理密码输入
                    import shlex
                    # 对于sudo命令，我们使用os.system让其直接在终端中执行
                    # 这样可以保留终端的所有功能，包括密码输入
                    returncode = os.system(command)
                    
                    # 处理退出码（Windows和Unix系统的退出码表示方式不同）
                    if os.name == 'nt':
                        returncode = returncode
                    else:
                        returncode = returncode // 256
                    
                    stdout_lines = []
                    stderr_lines = []
                    
                    if not self.config.get("quiet_mode", False) and returncode != 0:
                        print(f"退出码: {returncode}")
                    
                    # 将输出保存到日志文件
                    self._log_command_output(command, ''.join(stdout_lines), ''.join(stderr_lines), returncode)
                    
                    # 如果命令执行失败，获取大模型的建议
                    if returncode != 0:
                        self._get_error_solution_from_llm(command, ''.join(stdout_lines), ''.join(stderr_lines), returncode)
                    
                    return ''.join(stdout_lines), ''.join(stderr_lines), returncode
                except Exception as e:
                    print(f"执行sudo命令时出错: {e}")
                    return "", str(e), -1
            
            # 根据不同操作系统调整执行方式
            shell = True
            cmd = command
            
            # 统一参数设置，确保在WSL环境下也能正常工作
            process = subprocess.Popen(
                cmd,
                shell=shell,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # 行缓冲
            )
            
            # 在非Windows系统上添加start_new_session
            if os.name != 'nt':
                # 注意：start_new_session参数在Windows上不可用
                # 直接使用已经导入的subprocess模块，避免重复导入导致的作用域问题
                process = subprocess.Popen(
                    cmd,
                    shell=shell,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,  # 行缓冲
                    start_new_session=True  # 允许更好的进程管理
                )
            
            # 实时输出标准输出
            stdout_lines = []
            stderr_lines = []
            
            # 创建一个字典来跟踪每个流的状态
            streams = {
                process.stdout: {'buffer': stdout_lines, 'label': 'stdout'},
                process.stderr: {'buffer': stderr_lines, 'label': 'stderr'}
            }
            
            # 改进的实时输出逻辑，确保在WSL环境下正确显示结果
            import time
            start_time = time.time()
            
            # 先尝试直接读取和显示输出，适用于大多数简单命令
            try:
                # 实时读取stdout
                for line in process.stdout:
                    if line:
                        stdout_lines.append(line)
                        print(line, end='')
                        
                # 实时读取stderr
                for line in process.stderr:
                    if line:
                        stderr_lines.append(line)
                        if self._supports_color():
                            print(f"\033[91m{line}\033[0m", end='')  # 红色
                        else:
                            print(f"[错误] {line}", end='')
                            
            except Exception as e:
                print(f"直接读取输出时出错，尝试备用方法: {e}")
                # 如果直接读取失败，使用select作为备用方法
                import select
                readable = [process.stdout, process.stderr]
                
                while readable and time.time() - start_time < timeout:
                    # 等待流变为可读，设置超时为1秒
                    ready, _, _ = select.select(readable, [], [], 1.0)
                    
                    for stream in ready:
                        line = stream.readline()
                        if not line:
                            # 流已关闭
                            readable.remove(stream)
                            continue
                            
                        # 保存并输出行
                        streams[stream]['buffer'].append(line)
                        
                        # 为错误输出添加颜色标记（如果支持的话）
                        if stream == process.stderr:
                            if self._supports_color():
                                print(f"\033[91m{line}\033[0m", end='')  # 红色
                            else:
                                print(f"[错误] {line}", end='')
                        else:
                            print(line, end='')
                
            # 检查是否超时
            if time.time() - start_time >= timeout:
                print(f"\n命令执行超时（超过{timeout}秒），正在终止...")
                # 终止进程
                if os.name == 'nt':  # Windows
                    process.kill()
                else:  # Linux/Unix
                    try:
                        # 先尝试优雅终止
                        import signal
                        process.send_signal(signal.SIGTERM)
                        time.sleep(1)
                        if process.poll() is None:
                            process.kill()
                    except:
                        process.kill()  # 如果发送信号失败，直接杀死进程
                return -1
            
            # 等待进程完成并获取退出码
            returncode = process.wait()
            
            # 确保所有输出都被读取
            for stream in [process.stdout, process.stderr]:
                if stream in streams and not stream.closed:
                    remaining = stream.read()
                    if remaining:
                        streams[stream]['buffer'].append(remaining)
                        print(remaining, end='')
            
            print(f"\n{'='*60}")
            print(f"命令退出码: {returncode}")
            print(f"{'='*60}")
            
            # 将输出保存到日志文件
            self._log_command_output(command, ''.join(stdout_lines), ''.join(stderr_lines), returncode)
            
            # 如果命令执行失败，获取大模型的建议
            if returncode != 0:
                self._get_error_solution_from_llm(command, ''.join(stdout_lines), ''.join(stderr_lines), returncode)
            
            return ''.join(stdout_lines), ''.join(stderr_lines), returncode
            
        except KeyboardInterrupt:
            print("\n命令执行被用户中断")
            return -1
        except Exception as e:
            error_message = str(e)
            print(f"执行命令时出错: {error_message}")
            # 向大模型请求解决方案
            self._get_error_solution_from_llm(command, "", error_message, -1)
            return -1
            
    def _prepare_llm_request(self, model_config, prompt):
        """
        准备LLM请求的数据和头部信息

        Args:
            model_config: 模型配置信息
            prompt: 用户提示内容

        Returns:
            tuple: (url, headers, data)
        """
        # 构建基本请求头
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }

        # 构建基本消息
        messages = [
            {"role": "system", "content": "你是一位Linux系统专家。请分析命令执行失败的原因，并提供简洁明了的解决方案。"},
            {"role": "user", "content": prompt}
        ]

        # 根据模型类型构建不同的请求体
        endpoint = model_config.get('endpoint', '/chat/completions')
        
        # 确定要使用的模型ID（优先使用配置中的model_id，其次model_name，最后使用模型名称）
        model_id = model_config.get('model_id') or model_config.get('model_name', self.model)
        
        # 简化请求体，避免使用可能导致问题的特殊参数
        data = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        # Qwen3-32B模型需要使用extra_body传递enable_thinking参数
        if self.model == 'Qwen/Qwen3-32B':
            # 在非流式调用中需要enable_thinking=false
            if 'extra_body' not in data:
                data['extra_body'] = {}
            data['extra_body']['enable_thinking'] = False
        
        # 仅对MiniMax模型添加特殊处理
        if model_config['provider'] == 'modelscope' and self.model.startswith('minimax'):
            # MiniMax可能需要额外的头部信息
            headers['X-Minimax-GroupId'] = os.environ.get('MINIMAX_GROUP_ID', '')

        # 构建完整的请求URL
        url = f"{model_config['api_base_url']}{endpoint}"

        return url, headers, data
    
    def _parse_llm_response(self, response, color_output):
        """
        解析LLM响应并提取建议内容
        
        Args:
            response: API响应对象
            color_output: 是否使用彩色输出的颜色代码字典
        
        Returns:
            bool: 是否成功解析
        """
        YELLOW, GREEN, CYAN, RED, RESET = color_output.values()
        
        if response.status_code == 200:
            try:
                result = response.json()
                # 尝试不同的响应格式解析
                if 'choices' in result and len(result['choices']) > 0:
                    suggestion = result['choices'][0].get('message', {}).get('content', '')
                    
                    # 打印建议，使用绿色突出显示
                    print(f"\n{GREEN}解决方案建议:{RESET}")
                    print(f"{CYAN}{suggestion}{RESET}\n")
                    return True
                else:
                    print(f"{YELLOW}收到响应但格式不符合预期: {json.dumps(result, ensure_ascii=False, indent=2)}{RESET}")
            except json.JSONDecodeError:
                print(f"{RED}无法解析响应内容: {response.text}{RESET}")
        else:
            self._handle_api_error(response.status_code, response, color_output)
        
        return False
    
    def _handle_api_error(self, status_code, response, color_output):
        """
        处理API错误并提供详细的错误信息
        
        Args:
            status_code: HTTP状态码
            response: API响应对象
            color_output: 是否使用彩色输出的颜色代码字典
        """
        RED, YELLOW, RESET = color_output['RED'], color_output['YELLOW'], color_output['RESET']
        
        print(f"{RED}获取解决方案失败: HTTP {status_code}{RESET}")
        
        # 根据不同状态码提供更详细的错误信息
        error_details = {
            401: "身份验证失败，请检查API密钥是否正确",
            403: "访问被拒绝，可能是API密钥权限不足或已过期",
            429: "请求频率过高，请稍后再试",
            400: "请求参数错误，请检查输入",
            404: "请求的资源不存在",
            500: "服务器内部错误，请稍后再试",
            502: "网关错误，请检查服务状态",
            503: "服务不可用，请稍后再试",
            504: "网关超时，请检查网络连接"
        }
        
        if status_code in error_details:
            print(f"{RED}错误详情: {error_details[status_code]}{RESET}")
        else:
            print(f"{RED}未知错误状态码{RESET}")
        
        # 尝试获取错误响应内容
        try:
            error_data = response.json()
            if error_data:
                print(f"{YELLOW}错误响应内容:{RESET}")
                print(f"{YELLOW}{json.dumps(error_data, ensure_ascii=False, indent=2)}{RESET}")
        except:
            if response.text:
                print(f"{YELLOW}原始错误响应: {response.text[:500]}{RESET}")
                if len(response.text) > 500:
                    print(f"{YELLOW}[... 响应内容过长，已截断 ...]{RESET}")
    
    def _get_error_solution_from_llm(self, command, stdout, stderr, returncode):
        """
        当命令执行失败时，向大模型请求解决方案建议
        
        Args:
            command: 执行的命令
            stdout: 标准输出
            stderr: 标准错误
            returncode: 退出码
        """
        # 设置颜色输出
        if self._supports_color():
            color_output = {
                'YELLOW': '\033[93m',
                'GREEN': '\033[92m',
                'CYAN': '\033[96m',
                'RED': '\033[91m',
                'RESET': '\033[0m'
            }
        else:
            color_output = {
                'YELLOW': '',
                'GREEN': '',
                'CYAN': '',
                'RED': '',
                'RESET': ''
            }
        
        YELLOW, GREEN, CYAN, RED, RESET = color_output.values()
        
        print(f"\n{YELLOW}正在请求大模型获取解决方案建议...{RESET}")
        
        # 检查速率限制
        if not self._check_rate_limit():
            print(f"{RED}达到速率限制，请稍后再试{RESET}")
            return
        
        # 构建请求内容，限制输入长度
        max_content_length = 2000
        stdout_truncated = stdout[:max_content_length] + ("[...]" if len(stdout) > max_content_length else "")
        stderr_truncated = stderr[:max_content_length] + ("[...]" if len(stderr) > max_content_length else "")
        
        prompt = f"""
命令 '{command}' 执行失败，退出码为 {returncode}。

标准输出：
{stdout_truncated}

标准错误：
{stderr_truncated}

请提供可能的原因和解决方案建议。请使用简洁明了的语言，并且尽量提供具体的修复命令或步骤。
        """
        
        try:
            # 获取当前模型配置
            if self.model not in self.model_providers:
                print(f"{RED}未知模型: {self.model}{RESET}")
                print(f"{YELLOW}支持的模型列表: {', '.join(self.model_providers.keys())}{RESET}")
                return
            
            model_config = self.model_providers[self.model]
            
            if not self.api_key:
                print(f"{RED}无法获取{self.model}模型的API密钥，无法请求解决方案。{RESET}")
                print(f"{YELLOW}提示: 请设置环境变量 {model_config['api_key_env']} 或在配置文件中配置。{RESET}")
                return
            
            # 准备请求数据
            url, headers, data = self._prepare_llm_request(model_config, prompt)
            
            # 发送请求
            print(f"{YELLOW}使用模型: {self.model}，请求URL: {url}{RESET}")
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            # 记录请求
            self._record_request()
            
            # 解析响应
            self._parse_llm_response(response, color_output)
                
        except requests.exceptions.RequestException as e:
            print(f"{RED}网络请求失败: {str(e)}{RESET}")
            if isinstance(e, requests.exceptions.Timeout):
                print(f"{YELLOW}提示: 请求超时，请检查网络连接或稍后重试{RESET}")
            elif isinstance(e, requests.exceptions.ConnectionError):
                print(f"{YELLOW}提示: 连接失败，请检查API端点是否正确{RESET}")
            elif isinstance(e, requests.exceptions.RequestsJSONDecodeError):
                print(f"{YELLOW}提示: 无法解析响应JSON，请检查服务端状态{RESET}")
        except KeyboardInterrupt:
            print(f"\n{YELLOW}请求已取消{RESET}")
        except Exception as e:
            print(f"{RED}请求解决方案时出错: {str(e)}{RESET}")
            # 在调试模式下显示详细错误堆栈
            if self.config.get('debug', False):
                import traceback
                print(f"{RED}错误详情: {traceback.format_exc()}{RESET}")
            else:
                print(f"{YELLOW}提示: 开启调试模式可查看详细错误信息: set debug true{RESET}")
            
        return
    
    def _check_rate_limit(self):
        """检查是否超过API速率限制"""
        # 如果速率限制已关闭，直接返回True
        if not getattr(self, 'rate_limit_enabled', True):
            return True
            
        current_time = time.time()
        
        # 清理过期的请求记录
        self.rate_limit['requests'] = [t for t in self.rate_limit['requests'] 
                                     if current_time - t < 86400]  # 保留24小时内的记录
        
        # 计算不同时间段的请求数量
        requests_last_minute = sum(1 for t in self.rate_limit['requests'] 
                                 if current_time - t < 60)
        requests_last_hour = sum(1 for t in self.rate_limit['requests'] 
                                if current_time - t < 3600)
        requests_last_day = len(self.rate_limit['requests'])
        
        # 检查是否超过限制
        if requests_last_minute >= self.rate_limit['rpm']:
            wait_time = 60 - (current_time - min(self.rate_limit['requests'][-requests_last_minute:]))
            error_msg = f"速率限制: 已达到每分钟{self.rate_limit['rpm']}次请求的限制。请在{int(wait_time)}秒后重试。"
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return False
        
        if requests_last_hour >= self.rate_limit['rph']:
            error_msg = f"速率限制: 已达到每小时{self.rate_limit['rph']}次请求的限制。请稍后再试。"
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return False
        
        if requests_last_day >= self.rate_limit['rpd']:
            error_msg = f"速率限制: 已达到每天{self.rate_limit['rpd']}次请求的限制。请明天再试。"
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
            return False
        
        # 显示剩余请求次数（可选）
        remaining_rpm = self.rate_limit['rpm'] - requests_last_minute
        if remaining_rpm <= 3:
            warning_msg = f"警告: 您在当前分钟内仅剩{remaining_rpm}次请求"
            print(f"\033[93m{warning_msg}\033[0m" if self._supports_color() else warning_msg)
            
        return True
    
    def _record_request(self):
        """记录API请求的时间戳"""
        self.rate_limit['requests'].append(time.time())
        
    def _is_wsl(self):
        """检查是否在WSL环境中运行"""
        try:
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    return True
        except:
            pass
        return False
        
    def _supports_color(self):
        """检查终端是否支持颜色输出"""
        supported = False
        # 检查是否在终端中运行
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # 检查操作系统类型
            if sys.platform != 'win32' or 'ANSICON' in os.environ:
                supported = True
        return supported
    
    def _log_command_output(self, command, stdout, stderr, returncode):
        """将命令执行结果记录到日志文件"""
        try:
            # 创建日志目录
            log_dir = os.path.expanduser("~/.ecnu_shell_logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 生成日志文件名（按日期）
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(log_dir, f"shell_log_{today}.log")
            
            # 写入日志
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'='*80}\n")
                f.write(f"[{timestamp}] 命令: {command}\n")
                f.write(f"退出码: {returncode}\n")
                
                if stdout:
                    f.write("\n标准输出:\n")
                    f.write(stdout)
                
                if stderr:
                    f.write("\n错误输出:\n")
                    f.write(stderr)
                
                f.write(f"{'='*80}\n")
                
        except Exception as e:
            # 日志记录失败不应影响主程序
            pass
    
    def save_command_history(self):
        """保存命令历史到文件"""
        try:
            # 确定历史文件路径，考虑WSL环境
            if self._is_wsl():
                # 在WSL中，使用更可靠的路径存储方式
                history_file = os.path.join(os.path.expanduser("~"), ".ecnu_shell_history")
                print("在WSL环境中保存命令历史")
            else:
                # Windows或其他系统
                history_file = os.path.expanduser("~/.ecnu_shell_history")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            
            with open(history_file, 'a') as f:
                for cmd in self.command_history:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {cmd}\n")
                    
            # 可选：显示保存位置的提示
            if self.config.get('show_history_info', False):
                print(f"命令历史已保存到: {history_file}")
                
        except Exception as e:
            error_msg = f"保存命令历史失败: {e}"
            print(f"\033[91m{error_msg}\033[0m" if self._supports_color() else error_msg)
    
    def display_help(self):
        """显示帮助信息"""
        help_text = """
        Shell智能助手使用说明:
        ========================
        1. 基本使用:
           输入自然语言描述你想要执行的操作，系统会自动转换为Shell命令
           命令转换后，系统会询问是否执行该命令
        
        2. 特殊命令:
           - help/h: 显示此帮助信息
           - exit/quit/q: 退出程序
           - clear/cls: 清屏
           - history: 查看最近执行的命令
           - emblem/show_emblem: 显示华东师范大学校徽
           - config: 查看当前配置
           - config [key] [value]: 修改配置项
           - model: 查看当前模型
           - model [model_name]: 切换模型
           - rate_limit on/off: 开启/关闭速率限制功能
           - rate_limit status: 查看当前速率限制状态
        
        3. 实用功能:
           - 命令执行超时保护: 防止命令执行时间过长
           - 彩色输出: 在支持的终端中显示彩色错误信息
           - 执行日志: 自动记录命令执行历史和结果
        
        4. 配置管理:
           - 配置文件: ~/.ecnu_shell_config.json
           - 环境变量: 
             * ECNU_API_KEY (ECNU模型)
             * MODEL_SCOPE_API (魔搭社区模型)
        
        5. 支持的模型:
           - ECNU模型: ecnu-plus, ecnu-max, ChatECNU
           - 魔搭社区模型: minimax, minimax-m2
        
        6. 安全提示:
           - 执行命令前请仔细检查转换后的命令
           - 避免在生产环境中直接执行未知命令
           - 敏感操作请手动确认
           
        7. 助教模式:
           - teach: 进入助教模式，提供Linux命令学习功能
           - explain [自然语言]: 直接获取对自然语言的命令解释
           
           助教模式功能:
           * 输入自然语言，获取对应的Linux命令及详细解释
           * 输入Linux命令，获取命令详解及预期执行结果
        """
        print(help_text)
    
    def display_config(self):
        """显示当前配置"""
        print("\n当前配置:")
        print("==============")
        # 复制配置并隐藏API密钥
        config_display = self.config.copy()
        if "api_key" in config_display:
            api_key = config_display["api_key"]
            if len(api_key) > 8:
                config_display["api_key"] = api_key[:4] + "****" + api_key[-4:]
            else:
                config_display["api_key"] = "****"
        
        for key, value in config_display.items():
            print(f"{key}: {value}")
        print("==============\n")
        
        # 显示速率限制配置
        print("\n速率限制配置:")
        print(f"  每分钟请求限制(rpm): {self.rate_limit['rpm']}")
        print(f"  每小时请求限制(rph): {self.rate_limit['rph']}")
        print(f"  每天请求限制(rpd): {self.rate_limit['rpd']}")
        
        # 显示当前使用情况
        current_time = time.time()
        requests_last_minute = sum(1 for t in self.rate_limit['requests'] 
                                 if current_time - t < 60)
        print(f"  当前分钟已使用: {requests_last_minute}/{self.rate_limit['rpm']}")
        print("==============\n")
    
    def update_config(self, key, value):
        """更新配置项"""
        # 验证配置项是否有效
        valid_keys = ["api_base_url", "model", "max_history_size", "command_timeout", "temperature", "top_p", 
                     "show_ascii_banner", "badge_image_path", "use_colored_output"]
        
        if key not in valid_keys:
            print(f"无效的配置项: {key}")
            print(f"有效的配置项: {', '.join(valid_keys)}")
            return False
        
        # 转换值的类型
        if key == "max_history_size" or key == "command_timeout":
            try:
                value = int(value)
                if value <= 0:
                    raise ValueError("值必须为正数")
            except ValueError:
                print(f"配置项 {key} 必须是正整数")
                return False
        elif key == "temperature" or key == "top_p":
            try:
                value = float(value)
                if not (0 <= value <= 1):
                    raise ValueError("值必须在0到1之间")
            except ValueError:
                print(f"配置项 {key} 必须是0到1之间的浮点数")
                return False
        
        # 更新配置
        self.config[key] = value
        
        # 如果更新了模型，重新设置headers
        if key == "api_base_url":
            self.api_base_url = value
        elif key == "model":
            self.model = value
        
        # 保存配置
        self._save_config()
        print(f"配置项 {key} 已更新为: {value}")
        return True
    
    def set_model(self, model_name):
        """设置模型"""
        if model_name in self.available_models:
            if self._set_current_model(model_name):
                self.config["model"] = model_name
                self._save_config()
                return True
        return False
    
    def main(self):
        """主函数"""
        try:
            # 显示欢迎信息
            self._display_welcome()
            
            while True:
                try:
                    # 获取用户输入
                    user_input = input("\n\033[92m>>>\033[0m ").strip()
                    
                    # 处理特殊命令
                    if user_input.lower() in ['exit', 'quit', 'q']:
                        print("\n感谢使用Shell智能助手，再见！")
                        break
                    elif user_input.lower() in ['help', 'h']:
                        self.display_help()
                        continue
                    elif user_input.lower() in ['clear', 'cls']:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        self._display_welcome()
                        continue
                    elif user_input.lower() == 'history':
                        print("\n最近执行的命令:")
                        if not self.command_history:
                            print("  暂无执行历史")
                        else:
                            for i, cmd in enumerate(self.command_history[-10:], 1):
                                print(f"  {i}. {cmd}")
                        continue
                    elif user_input.lower().startswith('emblem_rgb'):
                        print("\n[显示华东师范大学校徽(彩色)]")
                        # 尝试使用term_image显示彩色图片校徽
                        self._display_color_image_badge()
                        print()
                        continue
                    elif user_input.lower().startswith('emblem') or user_input.lower().startswith('show_emblem'):
                        parts = user_input.lower().split()
                        print("\n[显示华东师范大学校徽]")
                        if len(parts) > 1:
                            if parts[1] == 'ascii':
                                # 显示ASCII校徽
                                if self._supports_color():
                                    BLUE = '\033[94m'
                                    BOLD = '\033[1m'
                                    RESET = '\033[0m'
                                else:
                                    BLUE = BOLD = RESET = ""
                                self._display_ascii_banner(BLUE, BOLD, RESET)
                            elif parts[1] == 'image':
                                # 显示图片校徽
                                self._display_image_badge()
                            else:
                                print("用法: emblem [ascii|image] - 不指定参数将显示默认校徽")
                                # 默认显示图片校徽
                                self._display_image_badge()
                        else:
                            # 默认显示图片校徽
                            self._display_image_badge()
                        print()
                        continue
                    elif user_input.lower().startswith('config'):
                        parts = user_input.split()
                        if len(parts) == 1:
                            self.display_config()
                        elif len(parts) == 3:
                            self.update_config(parts[1], parts[2])
                        else:
                            print("用法: config 或 config [key] [value]")
                        continue
                    elif user_input.lower().startswith('model'):
                        parts = user_input.split()
                        if len(parts) == 1:
                            print(f"当前模型: {self.model}")
                            print("可用模型:", ", ".join(self.available_models))
                        elif len(parts) == 2:
                            model_name = parts[1]
                            if self.set_model(model_name):
                                print(f"模型已切换到: {self.model}")
                            else:
                                print(f"无效的模型名称: {model_name}")
                                print("可用模型:", ", ".join(self.available_models))
                        else:
                            print("用法: model 或 model [model_name]")
                        continue
                    # 速率限制控制命令
                    elif user_input.lower() in ['rate_limit off', 'ratelimit off']:
                        self.rate_limit_enabled = False
                        print("✅ 速率限制已关闭")
                        continue
                    elif user_input.lower() in ['rate_limit on', 'ratelimit on']:
                        self.rate_limit_enabled = True
                        print("✅ 速率限制已开启")
                        continue
                    elif user_input.lower() in ['rate_limit status', 'ratelimit status']:
                        status = "开启" if self.rate_limit_enabled else "关闭"
                        print(f"📊 当前速率限制状态: {status}")
                        continue
                    # 助教模式命令
                    elif user_input.lower().startswith('teach'):
                        print("\n" + "="*50)
                        print("🎓 进入助教模式 - Linux命令学习助手")
                        print("="*50)
                        print("💡 使用说明:")
                        print("  • explain <描述>  - 将自然语言转换为Linux命令")
                        print("  • <命令>          - 解释Linux命令的语法和用法")
                        print("  • help            - 显示详细帮助")
                        print("  • exit            - 退出助教模式")
                        print("  • 直接按回车      - 不执行任何操作")
                        print("="*50)
                        print("🚀 开始你的Linux学习之旅！\n")
                        
                        # 助教模式循环
                        while True:
                            try:
                                teach_input = input("[助教模式] > ").strip()
                                
                                # 空输入处理 - 像正常命令行一样，不调用大模型
                                if not teach_input:
                                    continue
                                    
                                if teach_input.lower() == 'exit':
                                    print("\n退出助教模式")
                                    break
                                
                                # 显示模式帮助
                                if teach_input.lower() == 'help':
                                    print("\n" + "="*60)
                                    print("📚 助教模式 - 详细使用说明")
                                    print("="*60)
                                    print("🎯 模式1: 自然语言 → Linux命令")
                                    print("   用法: explain <你的描述>")
                                    print("   示例: explain 查看当前目录所有文件的权限")
                                    print("   功能: 将自然语言转换为具体的Linux命令，并提供详细解释")
                                    print()
                                    print("🎯 模式2: Linux命令 → 详细解释")
                                    print("   用法: 直接输入Linux命令")
                                    print("   示例: ls -la, pwd, mkdir test")
                                    print("   功能: 解释命令语法、参数含义和预期结果")
                                    print()
                                    print("💡 智能提示:")
                                    print("   • 输入help显示此帮助信息")
                                    print("   • 输入exit退出助教模式")
                                    print("   • 直接按回车不执行任何操作")
                                    print("   • 系统会自动识别自然语言和Linux命令")
                                    print("="*60)
                                    print()
                                    continue
                                
                                # 模式1: 自然语言转命令并解释
                                if teach_input.lower().startswith('explain '):
                                    natural_language = teach_input[8:].strip()
                                    if natural_language:
                                        print(f"🤔 正在将自然语言转换为Linux命令并解释: '{natural_language}'")
                                        self.explain_natural_language(natural_language)
                                    else:
                                        print("❌ 请输入需要解释的自然语言指令，例如: explain 列出当前目录的文件")
                                # 模式2: 命令解析
                                else:
                                    # 智能输入验证
                                    if len(teach_input) < 2:
                                        print("❌ 请输入有效的Linux命令，例如: ls, pwd, cd 等")
                                        continue
                                    
                                    # 检查是否为常见的无意义输入
                                    meaningless_inputs = ['', ' ', 'a', 'aa', 'test', 'abc', 'xxx']
                                    if teach_input.lower() in meaningless_inputs:
                                        print("💡 提示: 请输入具体的Linux命令，例如:")
                                        print("   • 文件操作: ls, cat, touch, mkdir, rm")
                                        print("   • 系统信息: pwd, whoami, ps, top")
                                        print("   • 网络工具: ping, curl, wget")
                                        continue
                                    
                                    # 检查是否可能是自然语言而非命令
                                    if ' ' in teach_input and len(teach_input) > 10:
                                        words = teach_input.lower().split()
                                        # 如果包含常见自然语言词汇，建议用户使用explain模式
                                        natural_language_words = ['how', 'what', 'where', 'list', 'show', 'create', 'delete', 'find', '我想', '请', '帮']
                                        if any(word in words for word in natural_language_words):
                                            print("💡 提示: 这看起来像是自然语言描述")
                                            print(f"   建议输入: explain {teach_input}")
                                            response = input("   是否自动转换?(y/n): ").lower()
                                            if response == 'y':
                                                self.explain_natural_language(teach_input)
                                                continue
                                    
                                    print(f"🔍 正在解释Linux命令: '{teach_input}'")
                                    success = self.explain_shell_command(teach_input)
                                    if not success:
                                        print("💡 提示: 命令解释失败，可能的原因:")
                                        print("   • 输入的不是标准Linux命令")
                                        print("   • 命令格式不正确")
                                        print("   • API调用失败")
                                        print("   请检查输入或尝试使用: explain <自然语言描述>")
                                    
                            except KeyboardInterrupt:
                                print("\n操作已取消")
                                continue
                        continue
                    # 快速使用解释功能
                    elif user_input.lower().startswith('explain '):
                        natural_language = user_input[8:].strip()
                        if natural_language:
                            self.explain_natural_language(natural_language)
                        else:
                            print("请输入需要解释的自然语言指令")
                        continue
                    elif not user_input:
                        continue
                    
                    # 将自然语言转换为Shell命令
                    shell_command = self.natural_language_to_shell(user_input)
                    
                    if shell_command:
                        # 安全检查
                        if self._is_dangerous_command(shell_command):
                            print("\033[91m警告: 检测到潜在危险命令！\033[0m")
                            confirm = input("确定要执行此命令吗？这可能会导致数据丢失或系统损坏！(yes/no): ")
                            if confirm.lower() != 'yes':
                                print("命令已取消执行")
                                continue
                        else:
                            # 显示转换后的命令并询问是否执行
                            # 使用分隔符显示命令
                            print()
                            print("=" * 20)
                            print(shell_command)
                            print("=" * 20)
                            print()
                            confirm = input("是否执行此命令？(y/n): ")
                            if confirm.lower() != 'y':
                                print("命令已取消执行")
                                continue
                        
                        # 执行命令
                        self.execute_shell_command(shell_command)
                        
                        # 限制历史记录大小
                        if len(self.history) > self.max_history_size:
                            self.history = self.history[-self.max_history_size:]
                            
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    continue
                except EOFError:
                    print("\n感谢使用Shell智能助手，再见！")
                    break
                except Exception as e:
                    print(f"\033[91m发生错误: {e}\033[0m")
                    # 记录错误日志
                    self._log_error(str(e))
                    continue
                    
        finally:
            # 保存命令历史
            self.save_command_history()
    
    def _display_welcome(self):
        """显示欢迎信息，包含ECNU标识"""
        # 清空屏幕（尝试）
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # 根据配置决定是否使用彩色输出
        use_color = self.config.get("use_colored_output", True) and self._supports_color()
        
        # 彩色输出设置
        BOLD = '\033[1m' if use_color else ''
        BLUE = '\033[94m' if use_color else ''
        GREEN = '\033[92m' if use_color else ''
        RESET = '\033[0m' if use_color else ''
        
        # 显示ASCII文本标识
        if self.config.get("show_ascii_banner", True):
            self._display_ascii_banner(BLUE, BOLD, RESET)
        
        print("=" * 56)
        print(f"{GREEN}{BOLD}{'Shell智能助手 (ChatECNU版)':^56}{RESET}")
        print("=" * 56)
        print(f"{'基于华东师范大学ChatECNU API的自然语言Shell助手':^56}")
        print(f"{'输入自然语言描述您想要执行的操作，系统将自动转换为Shell命令':^56}")
        print(f"{'输入 "help" 或 "h" 查看使用说明，输入 "exit" 或 "q" 退出':^56}")
        print("=" * 56)
        print()
        
    def _display_ascii_banner(self, blue, bold, reset):
        """使用figlet显示ECNU SHELL标识，添加更健壮的错误处理"""
        # 添加调试信息控制
        debug_mode = self.config.get("debug_mode", False)
        
        if has_figlet:
            try:
                # 获取可用字体列表（仅在调试模式下）
                if debug_mode:
                    try:
                        fonts = pyfiglet.FigletFont.getFonts()
                    except Exception:
                        pass
                
                # 尝试使用block字体，如果不可用则使用big字体
                font_used = None
                try:
                    ecnu_banner = pyfiglet.figlet_format("ECNU SHELL", font="block")
                    font_used = "block"
                except Exception:
                    # 如果block字体不可用，使用big字体
                    try:
                        ecnu_banner = pyfiglet.figlet_format("ECNU SHELL", font="big")
                        font_used = "big"
                    except Exception:
                        # 如果两种字体都失败，尝试不指定字体
                        try:
                            ecnu_banner = pyfiglet.figlet_format("ECNU SHELL")
                            font_used = "default"
                        except Exception:
                            raise  # 重新抛出异常，使用默认banner
                
                # 确保banner不为空
                if ecnu_banner and len(ecnu_banner.strip()) > 0:
                    print(f"{blue}{bold}{ecnu_banner}{reset}")
                else:
                    raise ValueError("生成的banner为空")
                    
            except Exception:
                # 如果figlet使用失败，使用默认的ASCII标识
                self._display_default_banner(blue, bold, reset)
        else:
            # 如果没有安装figlet，使用默认的ASCII标识
            self._display_default_banner(blue, bold, reset)
    
    def _display_default_banner(self, blue, bold, reset):
        """显示默认的ECNU ASCII文本标识（当figlet不可用时）"""
        ecnu_banner = r"""
  _____ ______ _   _ _     _          ____    _      _ _____   _____   _ 
 | ____|  ____| \ | | |   | |        |____|  | |    | |  ___| |  ___| | |
 |  _| | |    |  \| | |   | |        |____   | |____| | |___  | |___  | |
 | |___| |____| . ` | |___| |         ____|  | |    | |  ___| |  ___| | ___
 |_____|______|_|\__|_______|        |____|  |_|    |_|_____| |_____|_|_____|
        """
        print(f"{blue}{bold}{ecnu_banner}{reset}")
        
    def _display_image_badge(self):
        """显示图片校徽
        
        调用_display_image_in_terminal方法来显示华东师范大学校徽图片
        """
        try:
            # 调用新实现的图片显示函数
            self._display_image_in_terminal()
        except Exception as e:
            # 出错时显示后备信息
            print(f"[ECNU 校徽] 图片显示出错: {str(e)}")
            print()
            
    def _display_color_image_badge(self):
        """显示ECNU校徽
        
        使用pyfiglet显示photo文件夹下的ECNU_Emblem.svg.png相关文本
        """
        try:
            # 检查photo目录和图片文件存在
            photo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo")
            target_image = "ECNU_Emblem.svg.png"
            image_path = os.path.join(photo_dir, target_image)
            
            # 检查photo目录和图片文件
            if not os.path.exists(photo_dir):
                print(f"[提示] photo目录不存在，创建中...")
                os.makedirs(photo_dir)
            
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                print(f"[提示] 图片文件 '{target_image}' 存在于 photo 目录中")
            else:
                print(f"[提示] 正在使用 photo 目录下的 {target_image}")
            
            # 使用pyfiglet显示ECNU校徽相关文本
            if has_figlet:
                try:
                    # 尝试使用不同的字体显示ECNU
                    fonts_to_try = ["block", "big", "slant", "3-d", "3x5", "5lineoblique", "acrobatic"]
                    ecnu_text = "ECNU"
                    displayed = False
                    
                    for font in fonts_to_try:
                        try:
                            print(f"\n[使用 {font} 字体显示ECNU校徽文本]")
                            banner = pyfiglet.figlet_format(ecnu_text, font=font)
                            if banner and len(banner.strip()) > 0:
                                print(banner)
                                displayed = True
                                break
                        except Exception:
                            continue
                    
                    # 如果所有字体都失败，尝试默认字体
                    if not displayed:
                        print("\n[使用默认字体显示ECNU校徽文本]")
                        banner = pyfiglet.figlet_format(ecnu_text)
                        print(banner)
                    
                    # 显示额外信息
                    print(f"\n[华东师范大学校徽]")
                    print(f"图片文件位置: {image_path}")
                    
                except Exception as figlet_error:
                    print(f"[提示] pyfiglet显示出错: {str(figlet_error)}")
                    # 回退到简单文本显示
                    print("\nECNU - 华东师范大学")
            else:
                print("[提示] pyfiglet库不可用")
                # 回退到简单文本显示
                print("\nECNU - 华东师范大学")
                
        except Exception as e:
            # 出错时显示后备信息
            print(f"[ECNU 校徽] 显示出错: {str(e)}")
            print("\nECNU - 华东师范大学")
        
    def _display_background_watermark(self):
        """在欢迎界面显示校徽图片作为背景"""
        try:
            # 检查photo目录下是否有指定的图片文件
            photo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo")
            if not os.path.exists(photo_dir):
                print(f"\n[提示] photo目录不存在，创建中...")
                os.makedirs(photo_dir)
                return
            
            # 指定使用ECNU_Emblem.svg.png
            target_image = "ECNU_Emblem.svg.png"
            image_path = os.path.join(photo_dir, target_image)
            
            if os.path.exists(image_path):
                print("\n[ECNU 校徽显示]\n")
                
                # 尝试使用第三方库term_image直接显示图片
                term_image_success = False
                try:
                    # 添加导入诊断信息
                    print("[诊断] 尝试导入term_image库...")
                    import sys
                    print(f"[诊断] Python解释器路径: {sys.executable}")
                    print(f"[诊断] Python版本: {sys.version}")
                    
                    # 检查是否在虚拟环境中运行
                    in_venv = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
                    print(f"[诊断] 是否在虚拟环境中: {'是' if in_venv else '否'}")
                    if in_venv:
                        print(f"[诊断] 虚拟环境路径: {sys.prefix}")
                    else:
                        print("[诊断] 当前在系统Python中运行，不在虚拟环境中")
                    
                    # 获取终端宽度
                    try:
                        # 尝试使用shutil获取终端宽度
                        import shutil
                        terminal_width = shutil.get_terminal_size().columns
                        print(f"[诊断] 使用shutil获取终端宽度: {terminal_width} 列")
                    except:
                        # 回退到默认值
                        terminal_width = 80
                        print(f"[诊断] 无法获取终端宽度，使用默认值: {terminal_width} 列")
                    
                    # 简化的term_image导入尝试
                    try:
                        import term_image
                        print("[诊断] term_image库导入成功！")
                        
                        # 检查term_image库的主要功能
                        if hasattr(term_image, 'Image'):
                            # 尝试使用Image类
                            img = term_image.Image(image_path)
                            print(f"[诊断] 使用term_image.Image加载图片成功")
                            # 尝试显示图片
                            if hasattr(img, 'display'):
                                img.display()
                                print("[诊断] 图片显示完成")
                                term_image_success = True
                            elif hasattr(img, 'show'):
                                img.show()
                                print("[诊断] 图片显示完成")
                                term_image_success = True
                        elif hasattr(term_image, 'show'):
                            # 尝试直接使用show函数
                            term_image.show(image_path)
                            print("[诊断] 图片显示完成")
                            term_image_success = True
                    except Exception as term_error:
                        print(f"[诊断] term_image使用过程中出错: {str(term_error)}")
                    
                    if not term_image_success:
                        print("[诊断] term_image库版本兼容性问题，将回退到PIL库")
                except Exception as e:
                    print(f"[诊断] term_image处理过程中发生错误: {str(e)}")
                    print("[诊断] 将回退到PIL库")
                
                # 如果term_image不成功，显示详细的导入错误信息
                if not term_image_success:
                    print("[诊断] 详细信息:")
                    print("[诊断] 1. term_image库版本可能与当前Python环境不兼容")
                    # 确保使用sys.executable的基本名称，避免os模块依赖
                    python_exe_name = sys.executable.split('\\')[-1] if '\\' in sys.executable else sys.executable.split('/')[-1]
                    print(f"[诊断] 当前使用的Python解释器: {python_exe_name}")
                    print(f"[诊断] 当前环境: {sys.prefix}")
                    print("[诊断] 2. 将自动使用PIL库显示图片信息")
                    print("[诊断] 解决方法：")
                    print("[诊断] 1. term_image版本可能与代码不兼容")
                    print("[诊断] 2. 尝试使用PIL库代替（已实现自动回退）")
                    
                    # 如果term_image导入失败，尝试使用PIL作为备选方案
                    if has_pil:
                        print("\n[提示] 使用PIL显示图片信息")
                        from PIL import Image
                        
                        # 显示图片信息
                        img = Image.open(image_path)
                        width, height = img.size
                        print(f"[图片信息] 大小: {width}x{height}, 格式: {img.format}")
                        print("[提示] 提示：安装term_image库可获得更好的图片显示效果")
                    else:
                        print(f"[提示] 需要安装PIL库才能显示图片信息: pip install pillow")
                    print(f"图片路径: {image_path}")
            else:
                print(f"\n[提示] photo目录下没有找到指定的图片文件: {target_image}")
        except Exception as e:
            print(f"\n[提示] 校徽显示错误: {str(e)}")
    
    def _is_dangerous_command(self, command):
        """检查命令是否有潜在危险"""
        # 定义危险命令模式
        dangerous_patterns = [
            'rm.*-rf',  # 递归强制删除
            r'mkfs\.',  # 格式化文件系统
            'dd.*of=',   # 直接写入设备
            'chmod.*777', # 过于宽松的权限
            r'>.*\/etc\/',  # 覆盖系统配置文件
            r'\|\|.*rm',   # 失败后删除
            'shutdown',  # 关机
            'reboot',    # 重启
            'poweroff',  # 断电
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return True
        return False
    
    def _log_error(self, error_message):
        """记录错误日志"""
        try:
            log_dir = os.path.expanduser("~/.ecnu_shell_logs")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, "error.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] 错误: {error_message}\n")
        except:
            pass  # 出错时静默处理

    def _display_image_in_terminal(self, image_path=None):
        """
        在终端中显示图片（使用ASCII艺术方式）
        
        Args:
            image_path: 图片路径，如果为None则使用默认路径
            
        Returns:
            bool: 是否成功显示图片
        """
        try:
            # 如果没有提供图片路径，使用默认的校徽图片
            if image_path is None:
                photo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo")
                if not os.path.exists(photo_dir):
                    print(f"[提示] photo目录不存在，创建中...")
                    os.makedirs(photo_dir)
                    print(f"[提示] photo目录创建成功")
                    return False
                target_image = "ECNU_Emblem.svg.png"
                image_path = os.path.join(photo_dir, target_image)
        except Exception as e:
            print(f"[提示] 处理图片路径时出错: {str(e)}")
            return False

        if not os.path.exists(image_path):
            print(f"错误：找不到文件'{image_path}'")
            return False
        
        try:
            # 获取终端宽度用于自动调整图片尺寸
            terminal_width = shutil.get_terminal_size().columns
            
            # 使用PIL库将图片转换为ASCII字符艺术（主要方案）
            if has_pil:
                from PIL import Image
                # 打开图片并转换为灰度
                pil_image = Image.open(image_path).convert('L')
                
                # 调整尺寸为终端宽度的1/2
                width, height = pil_image.size
                aspect_ratio = height / width
                new_width = max(20, terminal_width // 2)  # 最小宽度为20列
                new_height = int(new_width * aspect_ratio * 0.5)  # 考虑字符高宽比
                
                # 调整图片大小
                resized = pil_image.resize((new_width, new_height))
                
                # 定义ASCII字符集（从暗到亮）
                ascii_chars = "@%#*+=-:. "
                
                # 转换为ASCII字符
                ascii_image = []
                for y in range(new_height):
                    line = []
                    for x in range(new_width):
                        pixel_value = resized.getpixel((x, y))
                        # 将像素值映射到ASCII字符
                        index = min(int(pixel_value * len(ascii_chars) / 256), len(ascii_chars) - 1)
                        line.append(ascii_chars[index])
                    ascii_image.append(''.join(line))
                
                # 打印ASCII艺术
                print("\n".join(ascii_image))
                print()
                return True
            else:
                # 如果PIL不可用，使用简单的文本提示
                print("[显示华东师范大学校徽]")
                return True
        except Exception as e:
            print(f"无法在终端中显示图片: {e}")
            # 最安全的回退方案
            print("[提示] 华东师范大学校徽")
            return False
     

def parse_arguments():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='Shell智能助手 - 基于ChatECNU API的自然语言Shell命令转换工具')
    
    # 添加命令行参数
    parser.add_argument('-c', '--config', help='指定配置文件路径')
    parser.add_argument('-m', '--model', help='指定使用的模型')
    parser.add_argument('-t', '--timeout', type=int, help='设置命令执行超时时间(秒)')
    parser.add_argument('-k', '--api-key', help='直接提供API密钥')
    
    return parser.parse_args()

           

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    try:
        # 创建助手实例
        assistant = ECNUShellAssistant()
        
        # 应用命令行参数覆盖配置
        if args.api_key:
            assistant.api_key = args.api_key
            assistant.headers["Authorization"] = f"Bearer {args.api_key}"
        
        if args.model:
            assistant.model = args.model
        
        if args.timeout:
            assistant.config["command_timeout"] = args.timeout
            
        # 启动主程序
        assistant.main()
    except Exception as e:
        print(f"程序异常退出: {e}")
        sys.exit(1)