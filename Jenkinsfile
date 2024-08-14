pipeline {
    agent any
    stages {
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t cynthion-test https://github.com/grvvy/cynthion-test.git#ppps_update'
            }
        }
        stage('Build') {
            agent {
                docker {
                    image 'cynthion-test'
                    reuseNode true
                    args '--name cynthion-test_container'
                }
            }
            steps {
                sh '''#!/bin/bash
                    git submodule init && git submodule update
                    cp /tmp/calibration.dat calibration.dat
                    make
                '''
            }
        }
        stage('Test') {
            agent {
                docker {
                    image 'cynthion-test'
                    reuseNode true
                    args '''
                        --name cynthion-test_container
                        --group-add=46 --group-add=20 --device-cgroup-rule="c 189:* rmw"
                        --device-cgroup-rule="c 166:* rmw" --net=host
                        --volume /run/udev/control:/run/udev/control
                        --volume /dev/bus/usb:/dev/bus/usb
                        --device /dev/serial/by-id/usb-Black_Magic_Debug_Black_Magic_Probe_v1.9.1_7BB0778C-if00
                    '''
                }
            }
            steps {
                sh 'hubs all off'
                retry(3) {
                    sh 'hubs cyntest_tycho cyntest_greatfet cyntest_bmp reset'
                    sh 'make unattended'
                }
                sh 'hubs all reset'
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
