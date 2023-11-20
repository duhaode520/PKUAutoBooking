# AutoBooking

PKU智慧场馆自动预约的改良版 fork from: https://github.com/lyqqqqqqqqq/PKUAutoBookingVenues

[老版本README](./archive/README.md)

本次修改主要使用了[tt识图](http://www.ttshitu.com/)处理了智慧场馆更新后在提交订单时要求使用滑动验证码的问题

同时还改变了一下访问iaaa的逻辑增强鲁棒性，避免可能的验证码弹窗


## 说明

- 本工具采用 Python3 搭配 `selenium` 完成自动化操作，实现全自动预约场馆
- 使用[tt识图](http://www.ttshitu.com/)完成字符验证码的校验
- 支持基于[Server酱](https://sct.ftqq.com/)的微信推送功能，体验更佳
- 采用定时任务可实现定期（如每周）免打扰预约，请设置在三天前的11:55-12:00之间
- 第三方依赖包几乎只有 `selenium` 一个
- 由于我只测试过羽毛球场的预约，其他场馆只是理论上可行，如果出现任何问题，可以提issue
- 支持时间上的“或”关系，支持按照星期几设定时间，“或”是有先后处理的顺序的，排在前面的先处理
- 时间上的“与”关系可通过设置多份`config*.ini`文件实现, *可以为数字、大小写字母和下划线——新版本暂不支持
- `config`参数填写`config.ini`文件的名称，类型为字符串
- `lst_config`为config文件名称字符串构成的列表
- `Booker` 类单独处理每个`config.ini`文件,`muilti_run(lst_config)`并行处理`lst_config`列表中的所有`config.ini`，`sequence_run(lst_config)`按序处理
- 定时任务还未经过完全测试
- 部分代码和这个README引用自大佬的自动出入校报备项目 https://github.com/Bruuuuuuce/PKUAutoSubmit
- 注意这是会自动付款的！！！付款方式是校园卡，所以如果只是试一试的话，要记得手动取消预约退款！！！
- 如果校园卡余额不足也是会预约失败的


## 安装与需求

### Python 3

本项目需要 Python 3，可以从[Python 官网](https://www.python.org/)下载安装

### Packages

#### selenium

采用如下命令安装 `selenium`，支持 4.10.0 及以上版本：

```python
pip3 install selenium==4.10.0
```

## 基本用法

1. 将 `config.sample.ini` 文件重命名为 `config0.ini` ，如果需要多个账号预约，或者需要时间上的“与”关系，请设置多个.ini文件（最多为两位数），
   请不要新建文件，不然自己搞定编码问题

2. 用文本编辑器（建议代码编辑器）打开 `config0.ini` 文件

3. 配置 `[login]` 、`[tt]`、`[type]` 、`[time]`、`[wechat_notice]` 这几个 Section 下的变量，在 `config0.ini.sample` 文件内有详细注释

4. [tt识图](http://www.ttshitu.com/)需要提前注册，每一次识别需要1分钱，大概充1块就可以使用很久了。

## 定时运行

### Windows

本项目中的 `autoRun.bat` 文件可提供在静默免打扰情况下运行程序的选择，配合 Windows 任务计划管理可实现定期自动填报，具体请参考[Win10下定时启动程序或脚本](https://blog.csdn.net/xielifu/article/details/81016220)

### mac OS

进入项目根目录，以命令 `./macAutoRun.sh` 执行 `macAutoRun.sh` 脚本即可，可设定或取消定时运行

### Linux

使用 `crontab` 设置

**Note:** 静默运行的弊端为无法看到任何报错信息，若程序运行有错误，使用者很难得知。故建议采用定时静默运行时，设置微信推送，在移动端即可查看到备案成功信息。

## 微信推送

本项目支持基于[Server酱](https://sct.ftqq.com/)的微信推送功能，仅需登录并扫码绑定，之后将获取到的 SCKEY 填入 `config0.ini` 文件即可，每日有5次免费推送，基本够用

会推送两次

1. 锁定场次的时候
2. 完成支付时

所以如果只接受到了一次推送，记得及时付款，否则会自动取消

## 责任须知

- 本项目仅供参考学习，造成的一切后果由使用者自行承担

## 证书

[Apache License 2.0](https://github.com/yanyuandaxia/PKUAutoBookingVenues/blob/main/LICENSE)

## 修改记录

### v3.0.2
- 重写了一些重试的逻辑，减少了高峰期的重试代价
- selenium 版本支持了4.10+
- 加入了对于 webdriver 的自动检查（目前支持 chrome）

### v3.0.1
- 增加了config的支持
  - config 支持更多样的命名形式
  - config 中现在有一个参数来确认这个config有没有被启用
- 忽略了 selenium 的控制台警告，控制台日志会更清爽
- 修复了部分已知的bug
### v3.0.0

- 重构了主要的预定代码，现在全部的预定代码都封装在了 `Booker` 类中
- 用装饰器函数封装了状态判断和错误捕捉的部分，简化了代码逻辑
- 使用 logger 进行控制台和文本的 log 输出，这样在 crash 时也可以拿到输出结果
- 优化了大部分浏览器元素的查找逻辑，尽量不使用可读性较差的 Xpath 进行查找
