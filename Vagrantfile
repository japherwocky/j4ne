# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # Ubuntu 14
    config.vm.define "local" do |local|
        local.vm.box = "ubuntu/trusty64"

        # BASE PROVISIONING
        local.vm.provision "ansible" do |ansible|
            ansible.verbose = "v"
            ansible.playbook = "sys/playbook.yml"
            ansible.extra_vars = { 
                vagrant_env: "local", 
            }
        end

        # LOCAL / DEV / DEFAULT PROVIDER OPTIONS
        local.vm.provider "virtualbox" do |vb|
            #   # Use VBoxManage to customize the VM. For example to change memory:
            #   vb.customize ["modifyvm", :id, "--memory", "1024"]
    
            # mirror the repo to the dev machine
            local.vm.synced_folder "./", "/opt/j4ne",
                owner: 1313,
                group: 1313,
                mount_options: ["dmode=775,fmode=755"]
    
    
            # forward port 80, view locally as http://localhost:8080
            local.vm.network "forwarded_port", guest: 80, host: 8080
    
            # Create a private network, which allows host-only access to the machine
            # eg, http://192.168.33.13
            # use with /etc/hosts/ to set subdomains
            local.vm.network "private_network", ip: "192.168.33.13"
    
        end

    end

end
