# Run behind Nginx and Gunicorn

In production, run the SimDB server as a WSGI service behind a dedicated web
server. This guide uses Gunicorn as the WSGI server and Nginx as the
proxy/load-balancer. It assumes Nginx and Gunicorn are already installed.

## Set up the Gunicorn service

Copy the init script from `src/simdb/remote/scripts/simdb.initd` in the SimDB
install directory to `/etc/init.d/simdb`.

Edit two lines in it:

- `USER=simdb` to the user the workers should run as.
- `DAEMON=/home/simdb/venv/bin/gunicorn` to the `gunicorn` in your virtual
  environment (find it with `which gunicorn` while the venv is active).

Start and check the service:

```bash
service simdb start
service simdb status
```

## Set up Nginx

Create `/etc/nginx/conf.d/simdb.conf`:

```nginx
server {
    listen 80;
    server_name localhost;   # or the server's address

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/run/simdb.sock;
    }
}
```

The packaged `src/simdb/remote/scripts/simdb.nginx` can be copied instead. The
`proxy_pass` target must match the `BIND` value in the init script.

If `/etc/nginx/proxy_params` does not exist, create it:

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Make sure `/etc/nginx/nginx.conf` includes `/etc/nginx/conf.d/*.conf` inside its
`http {}` block, then reload:

```bash
service nginx restart
```

## Allow large uploads

Simulation uploads can be large. Raise the body-size limit (at least 100 MB) in
`/etc/nginx/nginx.conf`:

```nginx
client_max_body_size 100m;
```

## Enable HTTPS

For production, terminate TLS at Nginx. See [Enable SSL](enable-ssl.md).
