nwyze9qop1b8   exec.cachemount   0B        21 hours ago     21 hours ago     1         false
pd3vd89e94x0   regular           0B        21 hours ago     21 hours ago     1         true
owh84w9dq5l8   regular           1.7kB     21 hours ago     21 hours ago     1         true
bh5581e7ocxp   regular           231kB     21 hours ago     21 hours ago     1         true
wxbmuigbssuw   regular           0B        21 hours ago     21 hours ago     1         true
q7x649iz8tjq   regular           245MB     21 hours ago     21 hours ago     1         true
4wk0z7x5l9j5   regular           0B        21 hours ago     21 hours ago     1         true
mk0oef76ioi6   regular           0B        21 hours ago     21 hours ago     1         true
y5p6kczezrw7   regular           4.67MB    21 hours ago     21 hours ago     1         true
t2b28tbyaamz   regular           0B        21 hours ago     21 hours ago     1         true
64kw0bh26e4x   regular           318B      8 hours ago      8 hours ago      1         true
ddiabnbl0h10   regular           1.76kB    8 hours ago      8 hours ago      1         true
2gtdejm0moqf   regular           870MB     8 hours ago      8 hours ago      1         true
iii4hkisvbu2   regular           2.07kB    8 hours ago      8 hours ago      1         true
v8uatxhwgc8x   regular           2.48kB    8 hours ago      8 hours ago      1         true
0tplkab1bp8m   regular           461MB     8 hours ago      8 hours ago      1         false
xdmawfplylu6   regular           1.76kB    8 hours ago      8 hours ago      1         true
oezxbp0gizyr   regular           870MB     8 hours ago      8 hours ago      1         true
t3foyeigweh0   regular           2.07kB    8 hours ago      8 hours ago      1         true
924s4su42jke   regular           318B      8 hours ago      8 hours ago      1         true
ltp95ll4viiq   regular           870MB     8 hours ago      8 hours ago      1         true
h711z8zzbr18   regular           1.76kB    8 hours ago      8 hours ago      1         true
f84w0kxayhew   regular           318B      8 hours ago      8 hours ago      1         true
c2dk5pj1pc9u   regular           2.07kB    8 hours ago      8 hours ago      2         true
luegsx5pr3wn   regular           1.23GB    8 hours ago      6 hours ago      6         true
dfl0peqmzsj3   regular           1.76kB    6 hours ago      6 hours ago      1         true
xa1xp8onvuj3   regular           318B      6 hours ago      6 hours ago      1         true
9plkeydlxedp   regular           870MB     6 hours ago      6 hours ago      1         true
obbpmuc91a6u   regular           2.07kB    6 hours ago      6 hours ago      2         true
13nreyerf9cs   source.local      103B      21 hours ago     26 minutes ago   3         false
dhbsbx9k3jfh   source.local      231kB     21 hours ago     26 minutes ago   3         false
2m0elibwibyg   source.local      2.15kB    21 hours ago     26 minutes ago   3         false
doq3dph0o6kd   regular           1.7kB     21 hours ago     26 minutes ago   3         true
iwvys94mbxt5   exec.cachemount   264MB     21 hours ago     25 minutes ago   3         false
yeuza3j1vhvf   regular           1.23GB    25 minutes ago   25 minutes ago   1         true
bbd5r8tvgix8   regular           870MB     25 minutes ago   25 minutes ago   1         true
k2xcqrckc9xl   regular           18.7MB    21 hours ago     25 minutes ago   3         true
l39b7e03x73w   regular           2.5kB     26 minutes ago   25 minutes ago   1         true
m77lsf2m83en   regular           318B      25 minutes ago   25 minutes ago   1         true
y23ufbc6scma   regular           1.76kB    25 minutes ago   25 minutes ago   1         true
y5ba6iyk1gqp   regular           2.07kB    25 minutes ago   24 minutes ago   2         true
vyfzrt6znen8   source.local      922B      21 hours ago     24 minutes ago   10        false
wlv97qfu4rx9   source.local      870MB     21 hours ago     24 minutes ago   11        false
eeiwohzdj06n   frontend          0B        21 hours ago     24 minutes ago   11        false
old2at89xm4t   source.local      1.36kB    21 hours ago     24 minutes ago   10        false
/Users/melle/Github/email-ai-tinder: colima stop
INFO[0000] stopping colima                              
INFO[0000] stopping ...                                  context=docker
INFO[0000] stopping ...                                  context=vm
INFO[0003] done                                         
/Users/melle/Github/email-ai-tinder: colima start
INFO[0000] starting colima                              
INFO[0000] runtime: docker                              
INFO[0001] starting ...                                  context=vm
INFO[0012] provisioning ...                              context=docker
INFO[0013] starting ...                                  context=docker
INFO[0014] done                                         
/Users/melle/Github/email-ai-tinder: clear



/Users/melle/Github/email-ai-tinder: docker compose -f docker-compose.dev.yml up  
[+] Running 8/8
 ✔ Network mailmind-dev-network     Created                                                                                                                                                                0.0s 
 ✔ Container mailmind-dev-postgres  Created                                                                                                                                                                0.1s 
 ✔ Container mailmind-dev-redis     Created                                                                                                                                                                0.1s 
 ✔ Container mailmind-dev-frontend  Created                                                                                                                                                                0.1s 
 ✔ Container mailmind-dev-qdrant    Created                                                                                                                                                                0.1s 
 ✔ Container mailmind-dev-backend   Created                                                                                                                                                                0.0s 
 ✔ Container mailmind-dev-worker    Created                                                                                                                                                                0.0s 
 ✔ Container mailmind-dev-caddy     Created                                                                                                                                                                0.0s 
Attaching to mailmind-dev-backend, mailmind-dev-caddy, mailmind-dev-frontend, mailmind-dev-postgres, mailmind-dev-qdrant, mailmind-dev-redis, mailmind-dev-worker
mailmind-dev-frontend  | Entrypoint: Running npm install (will update dependencies)...
mailmind-dev-postgres  | 
mailmind-dev-postgres  | PostgreSQL Database directory appears to contain a database; Skipping initialization
mailmind-dev-postgres  | 
mailmind-dev-redis     | 1:C 24 Apr 2025 13:14:05.818 # WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition. Being disabled, it can also cause failures without low memory condition, see https://github.com/jemalloc/jemalloc/issues/1328. To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
mailmind-dev-redis     | 1:C 24 Apr 2025 13:14:05.820 * oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
mailmind-dev-redis     | 1:C 24 Apr 2025 13:14:05.820 * Redis version=7.4.2, bits=64, commit=00000000, modified=0, pid=1, just started
mailmind-dev-redis     | 1:C 24 Apr 2025 13:14:05.820 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/redis.conf
mailmind-dev-redis     | 1:M 24 Apr 2025 13:14:05.820 * monotonic clock: POSIX clock_gettime
mailmind-dev-redis     | 1:M 24 Apr 2025 13:14:05.822 * Running mode=standalone, port=6379.
mailmind-dev-redis     | 1:M 24 Apr 2025 13:14:05.822 * Server initialized
mailmind-dev-redis     | 1:M 24 Apr 2025 13:14:05.822 * Ready to accept connections tcp
mailmind-dev-qdrant    |            _                 _    
mailmind-dev-qdrant    |   __ _  __| |_ __ __ _ _ __ | |_  
mailmind-dev-qdrant    |  / _` |/ _` | '__/ _` | '_ \| __| 
mailmind-dev-qdrant    | | (_| | (_| | | | (_| | | | | |_  
mailmind-dev-qdrant    |  \__, |\__,_|_|  \__,_|_| |_|\__| 
mailmind-dev-qdrant    |     |_|                           
mailmind-dev-qdrant    | 
mailmind-dev-qdrant    | Version: 1.14.0, build: 3617a011
mailmind-dev-qdrant    | Access web UI at http://localhost:6333/dashboard
mailmind-dev-qdrant    | 
mailmind-dev-qdrant    | 2025-04-24T13:14:05.880378Z  INFO storage::content_manager::consensus::persistent: Loading raft state from ./storage/raft_state.json    
mailmind-dev-postgres  | 2025-04-24 13:14:05.892 UTC [1] LOG:  starting PostgreSQL 15.12 on aarch64-unknown-linux-musl, compiled by gcc (Alpine 14.2.0) 14.2.0, 64-bit
mailmind-dev-postgres  | 2025-04-24 13:14:05.893 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
mailmind-dev-postgres  | 2025-04-24 13:14:05.893 UTC [1] LOG:  listening on IPv6 address "::", port 5432
mailmind-dev-qdrant    | 2025-04-24T13:14:05.893940Z  INFO qdrant: Distributed mode disabled    
mailmind-dev-qdrant    | 2025-04-24T13:14:05.894417Z  INFO qdrant: Telemetry reporting enabled, id: 8c7c2693-0183-41cf-90b8-c40d54793194    
mailmind-dev-qdrant    | 2025-04-24T13:14:05.896080Z  INFO qdrant: Inference service is not configured.    
mailmind-dev-postgres  | 2025-04-24 13:14:05.896 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
mailmind-dev-qdrant    | 2025-04-24T13:14:05.899732Z  INFO qdrant::actix: TLS disabled for REST API    
mailmind-dev-qdrant    | 2025-04-24T13:14:05.900352Z  INFO qdrant::actix: Qdrant HTTP listening on 6333    
mailmind-dev-qdrant    | 2025-04-24T13:14:05.900363Z  INFO actix_server::builder: Starting 1 workers
mailmind-dev-qdrant    | 2025-04-24T13:14:05.900366Z  INFO actix_server::server: Actix runtime found; starting in Actix runtime
mailmind-dev-postgres  | 2025-04-24 13:14:05.903 UTC [28] LOG:  database system was shut down at 2025-04-24 13:12:25 UTC
mailmind-dev-qdrant    | 2025-04-24T13:14:05.906611Z  INFO qdrant::tonic: Qdrant gRPC listening on 6334    
mailmind-dev-qdrant    | 2025-04-24T13:14:05.906683Z  INFO qdrant::tonic: TLS disabled for gRPC API    
mailmind-dev-postgres  | 2025-04-24 13:14:05.920 UTC [1] LOG:  database system is ready to accept connections
mailmind-dev-backend   | Postgres is up - executing migrations
mailmind-dev-backend   | Using DJANGO_SETTINGS_MODULE: config.settings.development
mailmind-dev-frontend  | npm verbose cli /usr/local/bin/node /usr/local/bin/npm
mailmind-dev-frontend  | npm info using npm@10.8.2
mailmind-dev-frontend  | npm info using node@v18.20.8
mailmind-dev-frontend  | npm verbose title npm install
mailmind-dev-frontend  | npm verbose argv "install" "--loglevel" "verbose" "--unsafe-perm" "true"
mailmind-dev-frontend  | npm verbose logfile logs-max:10 dir:/home/node/.npm/_logs/2025-04-24T13_14_06_078Z-
mailmind-dev-frontend  | npm verbose logfile /home/node/.npm/_logs/2025-04-24T13_14_06_078Z-debug-0.log
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2532978,"msg":"maxprocs: Leaving GOMAXPROCS=2: CPU quota undefined"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.253641,"msg":"GOMEMLIMIT is updated","package":"github.com/KimMachineGun/automemlimit/memlimit","GOMEMLIMIT":1849168281,"previous":9223372036854775807}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2549856,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2558885,"msg":"adapted config to JSON","adapter":"caddyfile"}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2559586,"msg":"Caddyfile input is not formatted; run 'caddy fmt --overwrite' to fix inconsistencies","adapter":"caddyfile","file":"/etc/caddy/Caddyfile","line":2}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2584605,"logger":"admin","msg":"admin endpoint started","address":"localhost:2019","enforce_origin":false,"origins":["//localhost:2019","//[::1]:2019","//127.0.0.1:2019"]}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2596517,"logger":"tls.cache.maintenance","msg":"started background certificate maintenance","cache":"0x4000413680"}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2624924,"logger":"http.auto_https","msg":"server is listening only on the HTTP port, so no automatic HTTPS will be applied to this server","server_name":"srv1","http_port":80}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.26259,"logger":"http.auto_https","msg":"server is listening only on the HTTPS port but has no TLS connection policies; adding one to enable TLS","server_name":"srv0","https_port":443}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2626526,"logger":"http.auto_https","msg":"enabling automatic HTTP->HTTPS redirects","server_name":"srv0"}
mailmind-dev-caddy     | {"level":"debug","ts":1745500446.2627103,"logger":"http.auto_https","msg":"adjusted config","tls":{"automation":{"policies":[{"on_demand":true}]}},"http":{"servers":{"srv0":{"listen":[":443"],"routes":[{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group12","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"frontend:8080"}]}]}]}]}],"tls_connection_policies":[{}],"automatic_https":{},"logs":{"default_logger_name":"log1"}},"srv1":{"listen":[":80"],"routes":[{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"backend:8000"}]}]}]}]},{"group":"group14","handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"frontend:8080"}]}]}]}]},{}],"automatic_https":{"disable":true},"logs":{"default_logger_name":"log0"}}}}}
mailmind-dev-caddy     | {"level":"debug","ts":1745500446.265542,"logger":"http","msg":"starting server loop","address":"[::]:443","tls":true,"http3":false}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.265665,"logger":"http","msg":"enabling HTTP/3 listener","addr":":443"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2657895,"msg":"failed to sufficiently increase receive buffer size (was: 208 kiB, wanted: 7168 kiB, got: 416 kiB). See https://github.com/quic-go/quic-go/wiki/UDP-Buffer-Sizes for details."}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2666662,"logger":"http.log","msg":"server running","name":"srv0","protocols":["h1","h2","h3"]}
mailmind-dev-caddy     | {"level":"debug","ts":1745500446.266915,"logger":"http","msg":"starting server loop","address":"[::]:80","tls":false,"http3":false}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2669766,"logger":"http","msg":"HTTP/2 skipped because it requires TLS","network":"tcp","addr":":80"}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2671418,"logger":"http","msg":"HTTP/3 skipped because it requires TLS","network":"tcp","addr":":80"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2672563,"logger":"http.log","msg":"server running","name":"srv1","protocols":["h1","h2","h3"]}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2672975,"logger":"tls","msg":"YOUR SERVER MAY BE VULNERABLE TO ABUSE: on-demand TLS is enabled, but no protections are in place","docs":"https://caddyserver.com/docs/automatic-https#on-demand-tls"}
mailmind-dev-caddy     | {"level":"warn","ts":1745500446.2686267,"logger":"pki.ca.local","msg":"installing root certificate (you might be prompted for password)","path":"storage:pki/authorities/local/root.crt"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2691407,"msg":"warning: \"certutil\" is not available, install \"certutil\" with \"apt install libnss3-tools\" or \"yum install nss-tools\" and try again"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.269149,"msg":"define JAVA_HOME environment variable to use the Java trust"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2720075,"logger":"tls","msg":"storage cleaning happened too recently; skipping for now","storage":"FileStorage:/data/caddy","instance":"3910f0b4-321a-4642-92a6-2197ad2e0298","try_again":1745586846.272007,"try_again_in":86399.999999743}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.272104,"logger":"tls","msg":"finished cleaning storage units"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.290661,"msg":"certificate installed properly in linux trusts"}
mailmind-dev-caddy     | {"level":"debug","ts":1745500446.290756,"logger":"events","msg":"event","name":"started","id":"310a7c8c-f316-4724-b314-6650d9052290","origin":"","data":null}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.291392,"msg":"autosaved config (load with --resume flag)","file":"/config/caddy/autosave.json"}
mailmind-dev-caddy     | {"level":"info","ts":1745500446.2913988,"msg":"serving initial configuration"}
mailmind-dev-backend   | /usr/local/lib/python3.11/site-packages/django_q/conf.py:179: UserWarning: Retry and timeout are misconfigured. Set retry larger than timeout,failure to do so will cause the tasks to be retriggered before completion.See https://django-q2.readthedocs.io/en/master/configure.html#retry for details.
mailmind-dev-backend   |   warn(
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/fsevents
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/win32-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/win32-ia32
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/win32-arm64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/sunos-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/openbsd-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/netbsd-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-s390x
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-riscv64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-ppc64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-mips64el
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-loong64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-ia32
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/linux-arm
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/freebsd-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/freebsd-arm64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/darwin-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/darwin-arm64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/android-x64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/android-arm64
mailmind-dev-frontend  | npm verbose reify failed optional dependency /app/node_modules/@esbuild/android-arm
mailmind-dev-frontend  | npm http fetch GET 200 https://registry.npmjs.org/npm 549ms
mailmind-dev-frontend  | npm http fetch POST 200 https://registry.npmjs.org/-/npm/v1/security/advisories/bulk 552ms
mailmind-dev-backend   | Operations to perform:
mailmind-dev-backend   |   Apply all migrations: account, admin, auth, authtoken, contenttypes, core, django_celery_beat, django_q, mfa, sessions, sites, socialaccount
mailmind-dev-backend   | Running migrations:
mailmind-dev-backend   |   No migrations to apply.
mailmind-dev-frontend  | npm http fetch GET 200 https://registry.npmjs.org/esbuild 196ms (cache miss)
mailmind-dev-backend   | Using DJANGO_SETTINGS_MODULE: config.settings.development
mailmind-dev-backend   | /usr/local/lib/python3.11/site-packages/django_q/conf.py:179: UserWarning: Retry and timeout are misconfigured. Set retry larger than timeout,failure to do so will cause the tasks to be retriggered before completion.See https://django-q2.readthedocs.io/en/master/configure.html#retry for details.
mailmind-dev-backend   |   warn(
mailmind-dev-frontend  | npm http fetch GET 200 https://registry.npmjs.org/vite 254ms (cache miss)
mailmind-dev-backend   | Superuser melleprise already exists.
mailmind-dev-backend   | Starting Daphne ASGI server...
mailmind-dev-frontend  | npm http fetch GET 200 https://registry.npmjs.org/@vitejs%2fplugin-react 241ms (cache miss)
mailmind-dev-frontend  | 
mailmind-dev-frontend  | up to date, audited 150 packages in 2s
mailmind-dev-frontend  | 
mailmind-dev-frontend  | 30 packages are looking for funding
mailmind-dev-frontend  |   run `npm fund` for details
mailmind-dev-frontend  | 
mailmind-dev-frontend  | 2 moderate severity vulnerabilities
mailmind-dev-frontend  | 
mailmind-dev-frontend  | To address all issues (including breaking changes), run:
mailmind-dev-frontend  |   npm audit fix --force
mailmind-dev-frontend  | 
mailmind-dev-frontend  | Run `npm audit` for details.
mailmind-dev-frontend  | npm verbose cwd /app
mailmind-dev-frontend  | npm verbose os Linux 6.8.0-50-generic
mailmind-dev-frontend  | npm verbose node v18.20.8
mailmind-dev-frontend  | npm verbose npm  v10.8.2
mailmind-dev-frontend  | npm notice
mailmind-dev-frontend  | npm notice New major version of npm available! 10.8.2 -> 11.3.0
mailmind-dev-frontend  | npm notice Changelog: https://github.com/npm/cli/releases/tag/v11.3.0
mailmind-dev-frontend  | npm notice To update run: npm install -g npm@11.3.0
mailmind-dev-frontend  | npm notice
mailmind-dev-frontend  | npm verbose exit 0
mailmind-dev-frontend  | npm info ok
mailmind-dev-frontend  | Entrypoint: npm install successful.
mailmind-dev-frontend  | Entrypoint: Starting application...
mailmind-dev-backend   | /usr/local/lib/python3.11/site-packages/django_q/conf.py:179: UserWarning: Retry and timeout are misconfigured. Set retry larger than timeout,failure to do so will cause the tasks to be retriggered before completion.See https://django-q2.readthedocs.io/en/master/configure.html#retry for details.
mailmind-dev-backend   |   warn(
mailmind-dev-frontend  | 
mailmind-dev-frontend  | > mailmind-frontend@0.1.0 dev
mailmind-dev-frontend  | > NODE_OPTIONS='--no-experimental-fetch' vite --host 0.0.0.0 --port 8080
mailmind-dev-frontend  | 
mailmind-dev-backend   | INFO 2025-04-24 13:14:08,291 cli 1 270776545738784 Starting server at tcp:port=8000:interface=0.0.0.0
mailmind-dev-backend   | INFO 2025-04-24 13:14:08,291 server 1 270776545738784 HTTP/2 support not enabled (install the http2 and tls Twisted extras)
mailmind-dev-backend   | INFO 2025-04-24 13:14:08,291 server 1 270776545738784 Configuring endpoint tcp:port=8000:interface=0.0.0.0
mailmind-dev-backend   | INFO 2025-04-24 13:14:08,292 server 1 270776545738784 Listening on TCP address 0.0.0.0:8000
mailmind-dev-frontend  | 
mailmind-dev-frontend  |   VITE v4.5.13  ready in 252 ms
mailmind-dev-frontend  | 
mailmind-dev-frontend  |   ➜  Local:   http://localhost:8080/
mailmind-dev-frontend  |   ➜  Network: http://172.18.0.2:8080/
mailmind-dev-worker    | Postgres is up - starting QCluster
mailmind-dev-worker    | Using DJANGO_SETTINGS_MODULE: config.settings.development
mailmind-dev-worker    | /usr/local/lib/python3.11/site-packages/django_q/conf.py:179: UserWarning: Retry and timeout are misconfigured. Set retry larger than timeout,failure to do so will cause the tasks to be retriggered before completion.See https://django-q2.readthedocs.io/en/master/configure.html#retry for details.
mailmind-dev-worker    |   warn(
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,712 cluster 1 274742809128992 Q Cluster oregon-uniform-lion-zebra starting.
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,747 worker 8 274742809128992 Process-ba1d2e437cb84b929c73edac30536b53 ready for work at 8
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,749 worker 9 274742809128992 Process-424636daf9a2497f85f381d1a8429906 ready for work at 9
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,751 cluster 7 274742809128992 Process-fb2b19110df74fc5a59f2159c9a3f24d guarding cluster oregon-uniform-lion-zebra [django_q:mailmind-dev:q]
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,750 monitor 10 274742809128992 Process-1ea69aa3c7004bcf9de15cd5c51f9d89 monitoring at 10
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,752 pusher 11 274742809128992 Process-d93d6ce9505e405ab3db650da43b3c65 pushing tasks at 11
mailmind-dev-worker    | INFO 2025-04-24 13:14:16,752 cluster 7 274742809128992 Q Cluster oregon-uniform-lion-zebra [django_q:mailmind-dev:q] running.


w Enable Watch
