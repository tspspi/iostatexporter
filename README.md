# Simple Python I/O statistic exporter for Prometheus on FreeBSD

This is a simple ```iostat``` exporter as provider for the [Prometheus  time series database
and monitoring system](https://prometheus.io/) written in Python. It uses
the [prometheus-client](https://github.com/prometheus/client_python) Python
package to do the main work of running the webservice and managing the gauges.
It's just a wrapper that periodically calls ```iostat``` to gather information
about disk I/O which is then provided on the specified TCP port where it's
collected by Prometheus at the specified scrape interval. This scraper
uses ```iostat``` to query the parameters __thus it only works on FreeBSD, not on Linux__.

Since this exporter scrapes the output of the CLI tools it may break with
any software update and might only work with particular versions of those
tools. It has been tested on:

* FreeBSD 11.2
* FreeBSD 12.2
* FreeBSD 12.3

## Exported metrics

For each disk the following parameters are exposed (using the device filename
as label):

* Reads per second (```iostat_rs```)
* Writes per second (```iostat_ws```)
* Kilobytes read per second (```iostat_krs```)
* Kilobytes written per second (```iostat_kws```)
* Milliseconds per read (```iostat_msr```)
* Milliseconds per write (```iostat_msw```)
* Milliseconds per operation (```iostat_mso```)
* Milliseconds per transaction (```iostat_mst```)
* Queue length (```iostat_qlen```)
* Busy percentage (```iostat_busy```)

## Installation

The package can either be installed from PyPI

```
pip install iostatexporter-tspspi
```

or form a package downloaded directly from the ```tar.gz``` or ```whl``` from
the [releases](https://github.com/tspspi/iostatexporter/releases):

```
pip install iostatexporter-tspspi.tar.gz
```

## Usage

```
usage: iostatexporter [-h] [-f] [--uid UID] [--gid GID] [--chroot CHROOT]
                      [--pidfile PIDFILE] [--loglevel LOGLEVEL]
                      [--logfile LOGFILE] [--port PORT] [--interval INTERVAL]

Iostat exporter daemon

optional arguments:
  -h, --help           show this help message and exit
  -f, --foreground     Do not daemonize - stay in foreground and dump debug
                       information to the terminal
  --uid UID            User ID to impersonate when launching as root
  --gid GID            Group ID to impersonate when launching as root
  --chroot CHROOT      Chroot directory that should be switched into
  --pidfile PIDFILE    PID file to keep only one daemon instance running
  --loglevel LOGLEVEL  Loglevel to use (debug, info, warning, error,
                       critical). Default: error
  --logfile LOGFILE    Logfile that should be used as target for log messages
  --port PORT          Port to listen on
  --interval INTERVAL  Interval in seconds in which data is gathered
```
