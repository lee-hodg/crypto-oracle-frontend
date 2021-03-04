# Crypto Oracle

This is just the lightweight web client counterpart to Crypto Oracle. Do training locally
with crypto-oracle, use the management command to sync the local and remote db tables, and this app will
simply display the results

# Package management

[Poetry](https://python-poetry.org/docs/) is used to manage dependencies.

To set up the existing project for poetry first execute

```python
poetry init
```

This will generate the `pyproject.toml` file, with the dependencies and dev dependencies

Virtual in the project dir

```
poetry config virtualenvs.in-project true
```
For convenience during development we also have the following dev dependencies

```python
django-debug-toolbar
coloredlogs
Werkzeug
django-extensions
```

Next run

```
poetry install
```

Adding and removing packages with poetry:

```bash
poetry add X --dev # dev only
poetry add Y  # non -dev
poetry remove Z  # remove
```

Updating

```bash
poetry update X
```

Generating a regular `requirements.txt`

```bash
poetry export -f requirements.txt > requirements.txt --without-hashes
```

The location of the virtualenv set up by poetry can be found by running

```bash
poetry config --list 
```


# AWS Deploy

## Database

First create the RDS instance and make a note of the credentials by
going [here](https://console.aws.amazon.com/rds/home?region=us-east-1#launch-dbinstance:gdb=false;s3-import=false)
and selecting `Standard Create` and `PostgreSQL`.
Choose Public Access (to make our life easier for pushing from local to prod for this app)
and choose or create a security group that has the 5432 port allowed from anywhere inbound.

Wait for it to be created and then record the hostname endpoint too.


## SSM Secrets


Set the sensitive variables in the
[SSM Parameter Store](https://console.aws.amazon.com/systems-manager/parameters/?region=us-east-1&tab=Table)
using the RDS credentials obtained above


```
/RDS/Name
/RDS/User
/RDS/Password
/RDS/Hostname
/RDS/Port
/Django/SecurityKey
```

### EBS

Allow EBS and EC2 access to read SSM parameters
Got [here](https://console.aws.amazon.com/iam/home#/roles) and select
the `aws-elasticbeanstalk-ec2-role` role then attach the `AmazonSSMReadOnlyAccess`
policy.

Ensure the EC2 security and RDS groups both allow access on the relevant port.


Install `awswebcli` on your system:

```bash
pip install --upgrade --user awsebcl
```

Add an AWS credentials profile to

```bash 
vim ~/.aws/credentials
```

For example

```bash 
[myprofile]
aws_access_key_id = XXXXX
aws_secret_access_key = XXXYYYZZZ
``

Then (use `-it t3.medium` if need bigger instance)

```bash
eb init --profile <myprofile>
eb create crypto-oracle-frontend --single -it t3.medium --profile <myprofile>
```


If some environment variable is missing it could lead to errors on one of the manage commands.

```
DJANGO_RUNTIME_ENVIRONMENT
RDS_DB_NAME
RDS_USERNAME
RDS_PASSWORD
RDS_HOSTNAME
RDS_PORT
DJANGO_SECRET_KEY
```

Note in AL2 the `PYTHONPATH` should already be set, and the method for installing
the postgres module has changed in `01_packages.config`


To debug issues check the logs and to run problematic commands:

```
# SSH into the server
eb ssh

# Load env variables
sudo su -
/opt/elasticbeanstalk/bin/get-config environment | jq -r 'to_entries | .[] | "export \(.key)=\"\(.value)\""' > /etc/profile.d/sh.local
sudo su ec2-user
source /etc/profile.d/sh.local

# Load virtualenv
cd /var/app
source venv/staging-LQM1lest/bin/activate
cd current

# Try command, e.g.
python manage.py collectstatic
```

Common issues to check:

- The security group of the [EC2 instance](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1) should allow
  postgres on 5432 inbound on any IP.
- Verify that the IAM service roles for ebs/ec2  have read-only ssm access (see above)
- RDS security group allows access from any IP on the relevant port, 5432
- If 400 code after successful deploy, check the allowed host matches the host EB provided.

Future deploys are with

```
eb deploy crypto-oracle-frontend --profile <myprofile>
```