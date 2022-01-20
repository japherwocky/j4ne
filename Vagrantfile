# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

    # Ubuntu 14
    config.vm.define "local" do |local|
        local.vm.box = "hashicorp/bionic64"

        # LOCAL / DEV / DEFAULT PROVIDER OPTIONS
        local.vm.provider "virtualbox" do |vb|
    
            # mirror the repo to the dev machine
            local.vm.synced_folder "./", "/opt/j4ne",
                owner: 1313,
                group: 1313 
    
            # forward port 80, view locally as http://localhost:8013
            local.vm.network "forwarded_port", guest: 80, host: 8013    
   
        end

    end

end
