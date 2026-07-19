在 PowerShell 里执行：

```
docker run -d `
  --name=maxkb `
  --restart=always `
  -p 8080:8080 `
  -v C:/maxkb:/opt/maxkb `
  registry.fit2cloud.com/maxkb/maxkb
```

启动后等 1-3 分钟初始化，然后打开：

<http://localhost:8080>

默认账号：

```
用户名：admin
密码：Admin123@
```

如果提示容器名已存在，先看状态：

```
docker ps -a --filter "name=maxkb"
```

如果已经存在但没启动：

```
docker start maxkb
```

如果 8080 端口被占用，改成 18080：

```
docker run -d `
  --name=maxkb `
  --restart=always `
  -p 18080:8080 `
  -v C:/maxkb:/opt/maxkb `
  registry.fit2cloud.com/maxkb/maxkb
```

然后访问：

<http://localhost:18080>

启动日志可看：

```
docker logs -f maxkb
```

看到服务初始化完成后，就可以进入页面创建知识库，上传我们生成的模拟资料包。
