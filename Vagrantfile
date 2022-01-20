# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

    # Ubuntu 14
    config.vm.define "local" do |local|
        local.vm.box = "ubuntu/trusty64"

        # LOCAL / DEV / DEFAULT PROVIDER OPTIONS
        local.vm.provider "virtualbox" do |vb|
            #   # Use VBoxManage to customize the VM. For example to change memory:
            #   vb.customize ["modifyvm", :id, "--memory", "1024"]
    
            # mirror the repo to the dev machine
            local.vm.synced_folder "./", "/opt/j4ne",
                owner: 1313,
                group: 1313  # ,
            #    mount_options: ["dmode=775,fmode=755"]
    
    
            # forward port 80, view locally as http://localhost:8080
            local.vm.network "forwarded_port", guest: 80, host: 8080
    
            # Create a private network, which allows host-only access to the machine
            # eg, http://192.168.33.13
            # use with /etc/hosts/ to set subdomains
            # local.vm.network "private_network", ip: "192.168.33.13"
    
        end

    end

end
