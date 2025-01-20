# xypro
A simple VLESS proxy implement

## Introdution

xypro is a simple proxy server that use socks5 inbound and send traffic to a VLESS server. 

It is a simple VLESS implementation, the goal is to learn Python asynchronous network programming. Plan to implement all supported protocols of Clash in the future.

Its configuration file is compatible with the clash proxy format. Here is an example:

```yaml
name: vless-ws-https-self-signed
uuid: bafcd0bd-5325-45af-8747-454ffd844784
server: 1.1.1.1
port: 443
serverName: an-example-server.com 
type: vless
udp: true
network: ws
tls: true
skip-cert-verify: true
ws-opts:
 headers:
   Host: an-example-server.com
 path: /an-example-path
```

To start a VLESS server, you can run the command.

```bash
git clone https://github.com/Safewoo/xypro.git
python -m xypro.run -f config.yaml
```

### Usage

#### VLESS

```yaml
name: vless-tcp
server: 172.17.101.95
port: 9090
type: vless
uuid: 27848739-7e62-4138-9fd3-098a63964b6b
network: tcp
tls: false
```

### VLESS with WebSocket

```yaml
name: vless-ws-https
uuid: bafcd0bd-5325-45af-8747-454ffd844784
server: 1.1.1.1
port: 443
serverName: an-example-server.com
type: vless
udp: true
network: ws
tls: true
skip-cert-verify: false
ws-opts:
 headers:
   Host: an-example-server.com
 path: /an-example-path
```


## Supported features

- [ ] Proxy Group
- [ ] Rule
- [ ] DNS 

### Supported inbound

- [x] Socks
- [ ] HTTP
- [ ] TUN
- [ ] Redirect TCP
- [ ] Tproxy TCP
- [ ] Tproxy UDP

### Supported protocols

- [x] VLESS
- [ ] VMess
- [ ] Trojan
- [ ] Shadowsocks

### Supported stream settings

- [x] tcp
- [x] websocket
- [ ] http2
