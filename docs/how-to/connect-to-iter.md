# Connect to ITER

This guide sets up the SimDB client to talk to the ITER server at
`simdb.iter.org`. It covers the remote configuration, the F5 firewall, and (for
ITER HPC nodes) installing the ITER SSL certificates.

## Add the ITER remote

On first run, SimDB pre-populates an `iter` remote. If you need to add it
manually:

```bash
simdb remote config new iter https://simdb.iter.org/scenarios/api/
simdb remote config set-option iter firewall F5
```

Listing the remotes should then show the F5 firewall:

```text
iter: https://simdb.iter.org/scenarios/api/ [firewall: F5]
```

Make it your default and set your ITER username:

```bash
simdb remote config set-default iter
simdb remote config set-option iter username <ITER_USERNAME>
```

## Test the connection

```bash
simdb remote iter list
```

or, if `iter` is your default:

```bash
simdb remote list
```

You will be asked for your ITER username and password, which are checked at the
F5 firewall.

```{important}
The ITER server authenticates at the F5 firewall and does **not** support SimDB
tokens, so `simdb remote token new` does not apply here. You authenticate
through the firewall on each session.
```

## Install the ITER SSL certificate (HPC nodes)

To use the client on an ITER HPC node you must trust the ITER CA certificates.
First download the root and issuing CA certificates:

```bash
wget "http://pki.iter.org/CertEnroll/io-ws-pkiroot_ITER%20Organization%20Root%20CA.crt"
wget "http://pki.iter.org/CertEnroll/io-ws-pki1.iter.org_ITER%20Organization%20Issuing%20CA1.crt"
```

Convert them to PEM and concatenate into one bundle, here `$HOME/iter.pem`:

```bash
openssl x509 -inform DER -in "io-ws-pki1.iter.org_ITER Organization Issuing CA1.crt" -out CA1.pem
openssl x509 -inform DER -in "io-ws-pkiroot_ITER Organization Root CA.crt" -out CA2.pem
cat CA1.pem CA2.pem > $HOME/iter.pem
```

Point SimDB at the bundle through the `SIMDB_REQUESTS_CA_BUNDLE` environment
variable:

```bash
export SIMDB_REQUESTS_CA_BUNDLE=$HOME/iter.pem
```

Add that line to `$HOME/.bash_profile` so it is set for every session.
