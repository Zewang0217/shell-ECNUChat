# Shell智能助手 (ChatECNU版)

基于华东师范大学ChatECNU API的自然语言Shell命令转换工具，支持Linux WSL环境。现已扩展支持魔搭社区GLM-4.6和Qwen3-32B模型，提供助教模式帮助学习Linux命令。

## 🌟 主要特性

- **🤖 多模型支持**：ECNU Chat、GLM-4.6、Qwen3-32B、MiniMax等
- **🎓 助教模式**：两种学习方式，帮助掌握Linux命令
- **🔄 动态切换**：运行时切换模型，无需重启
- **🛡️ 安全检查**：危险命令检测和用户确认
- **📚 智能解释**：自然语言转命令，命令语法详解
- **⚡ 实时执行**：转换后立即执行，支持结果展示
- **📖 历史记录**：命令历史保存，支持补全功能
- **🎯 WSL优化**：专为WSL环境优化的Shell助手
- **⚙️ 速率限制控制**：可灵活开启/关闭API请求限制，优化使用体验

## 如何添加API令牌

有三种方式可以添加API令牌：

### 方式1：环境变量（推荐）

**Linux/WSL (bash/zsh):**
1. 根据您要使用的模型提供商设置相应的环境变量：

   对于ECNU Chat模型：
   ```bash
   export ECNU_API_KEY="您的ECNU_API密钥"
   ```
   
   对于魔搭社区MiniMax模型：
   ```bash
   export MODEL_SCOPE_API="您的魔搭API密钥"
   ```

2. 或者将上述命令添加到`~/.bashrc`或`~/.zshrc`文件中以永久生效：
   ```bash
   echo 'export ECNU_API_KEY="您的API密钥"' >> ~/.bashrc
   source ~/.bashrc
   ```

**Windows PowerShell:**
```powershell
$env:ECNU_API_KEY="您的ECNU_API密钥"
$env:MODEL_SCOPE_API="您的魔搭API密钥"
```

**Windows Command Prompt (CMD):**
```cmd
set ECNU_API_KEY=您的API密钥
set MODEL_SCOPE_API=您的API密钥
```

> **重要提示：** Windows用户请注意，不同的命令行环境（PowerShell、CMD、WSL）需要分别设置环境变量。如果您在WSL中设置了环境变量，在PowerShell中运行程序时需要重新设置。

### 方式2：配置文件
1. 首次运行脚本后，配置文件将自动创建在`~/.ecnu_shell_config.json`（Linux/WSL）或`%USERPROFILE%\.ecnu_shell_config.json`（Windows）
2. 您也可以手动创建该文件并添加API密钥：
   ```json
   {
     "api_key": "默认API密钥",
     "api_keys": {
       "ecnu": "ECNU_API密钥",
       "modelscope": "魔搭API密钥"
     },
     "model": "ecnu-plus"
   }
   ```

您可以通过编辑此配置文件自定义以下配置项：
- `model`: 使用的模型名称（默认为'ecnu-plus'）
- `api_keys`: 不同模型提供商的API密钥
- `temperature`: 生成文本的随机性（0.0-1.0，默认为0.1）
- `top_p`: 核采样参数（0.0-1.0，默认为0.7）
- `history_size`: 命令历史记录大小（默认为100）
- `rate_limit_rpm`: 每分钟请求限制（默认为10）
- `rate_limit_rph`: 每小时请求限制（默认为60）
- `rate_limit_rpd`: 每天请求限制（默认为100）

### 支持的模型列表
程序支持多模型，包括ECNU Chat、魔搭社区GLM和Qwen模型，可通过`model`命令或配置文件进行切换。

**ECNU Chat模型:**
- `ecnu-plus`：默认模型，平衡性能和效果
- `ecnu-max`：更强的性能模型
- `ChatECNU`：基础模型

**魔搭社区GLM模型:**
- `GLM-4.6`：智谱AI的GLM-4.6模型，使用ZhipuAI/GLM-4.6模型ID

**魔搭社区Qwen模型:**
- `Qwen/Qwen3-32B`：通义千问3-32B模型，支持深度思考功能

### 方式3：命令行参数
运行时直接提供API密钥：
```bash
python3 ecnu_shell_assistant.py --api-key "您的API密钥"
```

## WSL环境准备

由于这是一个Linux Shell助手，推荐在WSL环境中使用：

1. **切换到WSL环境**：
   - 在Windows终端中输入`wsl`或打开WSL专用终端
   - 导航到脚本所在目录（可能需要挂载Windows驱动器）：
     ```bash
     cd /mnt/d/Zewang/大二上/Linux/shell/ecnu_shell_llm
     ```

2. **安装必要依赖**：
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   pip3 install requests pyfiglet
   ```
   
   > 说明：pyfiglet用于显示更好看的ECNU SHELL标识

3. **可选：命令行补全功能**：
   ```bash
   pip3 install readline
   ```

## Python虚拟环境设置

项目中已经创建了`myenv`虚拟环境，您可以按照以下步骤使用它：

### 使用现有虚拟环境
1. 在WSL终端中激活虚拟环境：
   ```bash
   cd /mnt/d/Zewang/大二上/Linux/shell/ecnu_shell_llm
   source myenv/bin/activate
   ```

2. 确认虚拟环境已激活（命令提示符前应显示`(myenv)`）：
   ```bash
   (myenv) zewang@redmi:/mnt/d/Zewang/大二上/Linux/shell/ecnu_shell_llm$ 
   ```

3. 在虚拟环境中安装依赖：
   ```bash
   pip install requests pyfiglet
   ```
   
   > 说明：pyfiglet用于显示更好看的ECNU SHELL标识

### 创建新的虚拟环境（如果需要）
如果需要创建新的虚拟环境，可以执行以下命令：
```bash
python3 -m venv newenv
source newenv/bin/activate
pip install requests pyfiglet
```

## 使用说明

### 基本使用
1. 设置API密钥：
   - Linux/WSL: `export ECNU_API_KEY="您的API密钥"`
   - Windows PowerShell: `$env:ECNU_API_KEY="您的API密钥"`
   - Windows CMD: `set ECNU_API_KEY="您的API密钥"`
   
   **重要提示**：
   - 在WSL环境中，环境变量仅在当前会话有效。如果希望永久设置，请将上述命令添加到`~/.bashrc`或`~/.zshrc`文件中
   - 对于频繁使用，可以使用以下命令使环境变量立即生效：`source ~/.bashrc`

2. 在WSL终端中运行：
   ```bash
   python3 ecnu_shell_assistant.py
   ```

2. 输入自然语言描述您想要执行的操作，例如：
   ```
   >>> 列出当前目录下的所有文件
   ```

3. 系统会将其转换为Shell命令并询问是否执行

### 命令行参数
```bash
python3 ecnu_shell_assistant.py [选项]
```

选项：
- `-k, --api-key`：指定API密钥
- `-m, --model`：指定使用的模型（默认：ecnu-plus）
- `-t, --timeout`：设置命令执行超时时间（秒）
- `-c, --config`：指定配置文件路径

### 内置命令
- `help/h`：显示帮助信息
- `exit/quit/q`：退出程序
- `clear/cls`：清屏
- `history`：查看最近执行的命令
- `config`：查看当前配置
- `config [key] [value]`：修改配置项
- `model`：查看当前模型
- `model [model_name]`：切换模型
- `rate_limit on/off`：开启/关闭速率限制功能
- `rate_limit status`：查看当前速率限制状态
- `teach`：进入助教模式，提供Linux命令学习功能

### 显示配置选项
程序新增了ECNU标识显示功能和相关配置选项：

```bash
# 控制是否显示ASCII文本标识
>>> config show_ascii_banner true

# 设置校徽图片路径（当获得图片后）
>>> config badge_image_path /path/to/ecnu_logo.png

# 控制是否使用彩色输出
>>> config use_colored_output true
```

当设置了有效的`badge_image_path`后，程序将优先显示图片校徽。目前程序已预留了图片校徽显示接口，在获得实际图片后可以轻松集成。

### 模型切换使用说明
程序支持在运行时动态切换ECNU Chat和魔搭社区MiniMax模型，无需重启程序：

```bash
# 查看当前模型
>>> model

# 切换到魔搭GLM-4.6模型
>>> model GLM-4.6

# 切换到魔搭Qwen3-32B模型  
>>> model Qwen/Qwen3-32B

# 切换到魔搭MiniMax模型
>>> model minimax

# 切换到魔搭MiniMax-M2模型
>>> model minimax-m2

# 切换回ECNU默认模型
>>> model ecnu-plus
```

切换模型后，后续的所有自然语言转Shell命令请求都将使用新选择的模型。

**注意事项：**
1. 使用不同厂商的模型需要设置对应的API密钥环境变量
2. 不同模型的API调用可能有不同的计费方式和限制
3. 某些模型可能对特定任务有更好的表现
4. Qwen3-32B模型使用`extra_body`参数进行特殊配置，确保非流式调用正常工作
5. GLM-4.6模型使用`ZhipuAI/GLM-4.6`作为模型ID，无需额外参数

## 助教模式 (Teach Mode)

程序提供专门的助教模式，帮助用户学习Linux命令，包含两种学习方式：

### 进入助教模式
```bash
>>> teach
```

### 模式1: 自然语言 → Linux命令 + 解释
将自然语言描述转换为具体的Linux命令，并提供详细解释：
```
[助教模式] > explain 查看当前目录所有文件的权限
🤔 正在将自然语言转换为Linux命令并解释: '查看当前目录所有文件的权限'
【命令】
ls -l

【解释】
ls -l 是Linux中用于以长格式列出目录内容的命令...
```

### 模式2: Linux命令 → 详细解释
解释现有Linux命令的语法、参数和用法：
```
[助教模式] > ls -la
🔍 正在解释Linux命令: 'ls -la'
【命令】
ls -la

【语法】
ls命令用于列出目录内容，参数说明：
- -l: 使用长格式显示，包含权限、所有者、大小等详细信息
- -a: 显示所有文件，包括隐藏文件（以.开头的文件）

【预期结果】
命令执行后将显示当前目录下所有文件和子目录的详细信息...
```

### 助教模式特色功能

1. **智能输入验证**
   - 空输入不会调用大模型（像正常命令行一样）
   - 自动识别无意义输入并给出建议
   - 检测到自然语言时建议使用explain模式

2. **友好错误处理**
   - 命令解释失败时给出具体建议
   - 输入过短或格式错误时提供指导

3. **增强用户体验**
   - 输入`help`显示详细使用说明
   - 彩色输出和清晰的格式标识
   - 支持键盘中断（Ctrl+C）取消操作

4. **智能提示系统**
   ```
   [助教模式] > help
   ==================================================
   📚 助教模式 - 详细使用说明
   ==================================================
   🎯 模式1: 自然语言 → Linux命令
      用法: explain <你的描述>
      示例: explain 查看当前目录所有文件的权限
      功能: 将自然语言转换为具体的Linux命令，并提供详细解释
   
   🎯 模式2: Linux命令 → 详细解释
      用法: 直接输入Linux命令
      示例: ls -la, pwd, mkdir test
      功能: 解释命令语法、参数含义和预期结果
   
   💡 智能提示:
      • 输入help显示此帮助信息
      • 输入exit退出助教模式
      • 直接按回车不执行任何操作
      • 系统会自动识别自然语言和Linux命令
   ==================================================
   ```

### 使用建议

1. **初学者**：多使用`explain`模式，学习如何将日常语言转换为Linux命令
2. **进阶用户**：使用模式2深入理解常用命令的高级用法
3. **错误排查**：当命令执行失败时，使用助教模式了解命令的正确用法
4. **日常练习**：定期使用助教模式巩固和扩展Linux知识

## 注意事项

1. **安全提示**：执行命令前请仔细检查转换后的命令，特别是涉及系统修改的操作
2. **网络连接**：确保WSL环境可以访问互联网以连接ChatECNU API
3. **API限制**：注意API调用频率限制，避免请求过于频繁
4. **日志文件**：执行日志保存在`~/.ecnu_shell_logs`目录
5. **命令历史记录**：执行的命令会保存在历史文件中，路径为：
   - Linux/WSL: `~/.ecnu_shell_history`
   - Windows: `%USERPROFILE%\.ecnu_shell_history`
   
   **WSL环境特别说明**：
   - 聊天历史会保存在WSL的用户主目录中，即使更新插件或重启WSL，历史记录也会保留
   - 程序会自动检测WSL环境并优化历史记录的保存路径
   - 如果遇到历史记录不保存的问题，请检查文件权限并确保您有写入权限

## 故障排除

### API调用失败
1. 检查API密钥是否正确设置
2. 确保网络连接正常
3. 查看错误信息，根据错误码进行排查
4. 可能是API服务暂时不可用，请稍后再试
5. 检查是否超过速率限制（见下方速率限制说明）
6. **Qwen3-32B模型特殊处理**：如果遇到`enable_thinking`参数错误，程序会自动使用`extra_body`方式处理
7. **GLM-4.6模型ID问题**：确保使用正确的模型ID `ZhipuAI/GLM-4.6`

### 速率限制说明

ECNU Chat API有以下速率限制：

- rpm: 每分钟请求限制（默认为10次）
- rph: 每小时请求限制（默认为60次）
- rpd: 每天请求限制（默认为100次）

当接近或达到限制时，程序会显示警告或错误提示。您可以通过修改配置文件自定义这些限制值，但建议不要超过API官方限制。

### WSL环境特定问题

1. **环境变量持久性**：在WSL中，环境变量设置不会自动持久化，请将设置命令添加到`.bashrc`或`.zshrc`文件

2. **文件权限**：如果遇到文件读写错误，请检查相关目录和文件的权限

3. **figlet显示问题**：在WSL中，如果ASCII艺术字显示异常，请确保已安装pyfiglet：
   ```bash
   pip install pyfiglet
   ```

4. **网络问题**：如果在WSL中遇到网络连接问题，请尝试重启WSL服务：
   ```bash
   wsl --shutdown
   ```
   然后重新启动WSL

### API令牌失效排查方案
如果遇到`401 - "无效的令牌"`错误，请按照以下步骤排查：

1. **检查API密钥格式**：
   - 确认API密钥没有多余的空格、换行符或特殊字符
   - 密钥可能区分大小写，请确保完全正确输入

2. **重新设置API密钥**：
   ```bash
   # 方式1：重新设置环境变量
   export ECNU_API_KEY="新的API密钥"
   
   # 方式2：更新配置文件
   # 编辑 ~/.ecnu_shell_config.json 文件，替换api_key字段
   ```

3. **验证API密钥是否正确传递**：
   - 使用命令行参数直接提供：`python3 ecnu_shell_assistant.py --api-key "您的API密钥"`
   - 这可以帮助排除环境变量或配置文件的问题

4. **检查API访问权限**：
   - 确认您的API密钥是否有访问ChatECNU模型的权限
   - 检查是否有使用次数或配额限制

5. **测试网络连接**：
   ```bash
   curl -I https://api.chatecnu.edu.cn/v1/chat/completions
   ```

6. **联系API支持**：如果以上方法都无效，可能需要联系华东师范大学API支持获取帮助

### 其他常见问题

- **命令无法执行**：确保转换的命令在当前WSL环境中有效
- **超时问题**：可以通过`--timeout`参数调整超时时间
- **依赖问题**：确保所有Python依赖已正确安装
- **语法警告**：代码中的无效转义序列警告已修复，不影响程序运行