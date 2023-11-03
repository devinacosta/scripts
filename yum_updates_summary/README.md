# Linux Update Scripts

The following scripts help solve the "remediation" step for CMRs. As a part of the Patching process we need to be able to revert back to previous version in case the upgrade goes sideways. The current problem is that CentOS/RedHat does not provide an easy way with YUM to determine what the previous version that was installed was.

The following scripts help solve this problem and provide a foul-proof way of knowing what to revert to in case needed.


# yum-updates-summary.py

The main purpose of this script is to get a list of all packages that will be upgraded during 'yum update' and then to capture all currently installed versions of those programs and then to output  a summary.

The script will output to screen a summary, it will also create a JSON file with all the data which can be used by additional scripts to easily roll back the versions automatically.

```
# yum-updates-summary.py

╭──────────────────────────┬───────────────────────────┬───────────────────────────╮
│ package                  │ current_version           │ update_version            │
├──────────────────────────┼───────────────────────────┼───────────────────────────┤
│ dnf-plugins-core         │ 4.3.0-5.el9_2             │ 4.3.0-5.el9_2.alma.1      │
│ glibc                    │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ glibc-common             │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ glibc-devel              │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ glibc-gconv-extra        │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ glibc-headers            │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ glibc-minimal-langpack   │ 2.34-60.el9               │ 2.34-60.el9_2.7           │
│ libnghttp2               │ 1.43.0-5.el9              │ 1.43.0-5.el9_2.1          │
│ linux-firmware           │ 20230310-134.el9_2.alma.1 │ 20230310-135.el9_2.alma.1 │
│ linux-firmware-whence    │ 20230310-134.el9_2.alma.1 │ 20230310-135.el9_2.alma.1 │
│ python3                  │ 3.9.16-1.el9_2.1          │ 3.9.16-1.el9_2.2          │
│ python3-devel            │ 3.9.16-1.el9_2.1          │ 3.9.16-1.el9_2.2          │
│ python3-dnf-plugins-core │ 4.3.0-5.el9_2             │ 4.3.0-5.el9_2.alma.1      │
│ python3-libs             │ 3.9.16-1.el9_2.1          │ 3.9.16-1.el9_2.2          │
╰──────────────────────────┴───────────────────────────┴───────────────────────────╯
```

# Examples of Usage

Obtain Yum Summary
> \# yum-updates-summary.py 

Display Pretty Version using JSON from previous run.
> \# yum-updates-summary.py -p


# Installation
Install Python3 PIP requirements.
> pip3 install -r requirements.txt

Ansible Job to deploy onto host (see ansible directory).
Be sure to update hosts file with hosts you are deploying to.

> ansible-playbook -u username -i hosts deploy_yum_updates_summary.yml  -k -K
