pipeline {
    agent {
        dockerfile {
            args '''
                --group-add=46 --group-add=20 --device-cgroup-rule="c 189:* rmw"
                --device-cgroup-rule="c 166:* rmw" --net=host
                --volume /run/udev/control:/run/udev/control
                --volume /dev/bus/usb:/dev/bus/usb
                --device /dev/serial/by-id/usb-Black_Magic_Debug_Black_Magic_Probe_v1.9.1_7BB0778C-if00
            '''
        }
    }
    triggers {
        cron(env.BRANCH_NAME == 'docker_bmp_fix' ? '*/5 * * * *' : '')
    }
    options { timestamps () }
    stages {
        stage('Build') {
            steps {
                sh '''#!/bin/bash
                    git submodule init && git submodule update
                    cp /tmp/calibration.dat calibration.dat
                    make
                '''
            }
        }
        stage('Test') {
            steps {
                sh 'lsusb'
                sh 'usbhub --disable-i2c --hub D9D1 power state --port 1,2,3,4 --off && sleep 1s'
                sh 'usbhub --disable-i2c --hub 624C power state --port 1,2,3,4 --off && sleep 1s'
                sh 'usbhub --disable-i2c --hub 624C power state --port 1,3,4 --on && sleep 1s'
                sh 'lsusb'
                sh 'lsusb -v -d 1d50:6018'
                sh 'make unattended'
            }
        }
    }
    post {
        always {
            cleanWs(cleanWhenNotBuilt: false,
                    deleteDirs: true,
                    disableDeferredWipeout: true,
                    notFailBuild: true)
        }
    }
}
