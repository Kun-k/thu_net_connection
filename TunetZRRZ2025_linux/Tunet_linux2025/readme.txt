校园网准入认证linux客户端使用说明

1.将auth-client和.auth-setting文件放到用户目录下。

2.更改auth-client文件权限为可执行。

3.登录：
	在用户目录下执行  ./auth-client -u 用户名 -p 用户密码 auth
	默认校内校外都可以访问。如果只访问校内网,需要加参数 --campus 用法如下：
	./auth-client -u 用户名 -p 用户密码 auth --campus

4.登出：
	在用户目录下执行 ./auth-client -u 用户名 auth --logout

5.帮助：
	在用户目录下执行./auth-client --help 以及 ./auth-client  auth  --help可以查看使用帮助
