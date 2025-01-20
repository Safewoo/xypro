# xypro
A simple VLESS proxy implementation

## Introduction

xypro is a simple proxy server that uses SOCKS5 inbound protocol and forwards traffic to a VLESS server. 

This is a basic VLESS implementation created to explore Python asynchronous network programming. Future plans include implementing all protocols supported by Clash.

The configuration file is compatible with the Clash proxy format. Here's an example:

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

To start a VLESS server, run the following command:


```bash
git clone https://github.com/Safewoo/xypro.git
python -m xypro.run -f config.yaml
```

## Configuration Examples

### Basic VLESS

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


### VLESS with Self-signed Certificate

```yaml
name: vless-ws-https-self-signed
uuid: bafcd0bd-5325-45af-8747-454ffd844784
server: 34.131.126.3
port: 443
serverName: hhoy.jncc.com
type: vless
udp: true
network: ws
tls: true
skip-cert-verify: true
ws-opts:
 headers:
   Host: hhoy.jncc.com
 path: /Sul4

```


## Supported features

### Core features

- [ ] Proxy Group
- [ ] Rule
- [ ] DNS 

### Inbound protocols

- [x] SOCKS
- [ ] HTTP
- [ ] TUN
- [ ] Redirect TCP
- [ ] Tproxy TCP
- [ ] Tproxy UDP

### Outbound protocols

- [x] VLESS
- [ ] VMess
- [ ] Trojan
- [ ] Shadowsocks

### Transport protocols (Stream)

- [x] TCP
- [x] Websocket
- [ ] HTTP/2
