import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_mapr_installed_packages(host):
    for p in [
        "mapr-zookeeper",
        "mapr-cldb",
        "mapr-fileserver",
        "mapr-resourcemanager",
        "mapr-historyserver",
        "mapr-webserver",
        "mapr-nodemanager",
        "mapr-core",
        "mapr-core-internal"
    ]:
        assert host.package(p).is_installed


def test_mapr_not_installed_packages(host):
    for p in [
        "mapr-nfs",
        "mapr-gateway",
        "mapr-posix-client-basic",
        "mapr-posix-client-platinum"
    ]:
        assert not host.package(p).is_installed


def test_mapr_configfiles(host):
    for f in [
        "maprserverticket",
        "cldb.key",
        ".customSecure",
        "ssl_keystore",
        "ssl_truststore",
        "ssl_truststore.pem"
    ]:
        assert host.file("/opt/mapr/conf/" + f).exists

def test_mapr_hadoop_configfiles(host):
    source_folder = "/opt/mapr/hadoop/hadoop-2.7.0/etc/hadoop/"
    for f in [
            "core-site.xml",
            "yarn-site.xml"
            ]:
        assert host.file(source_folder + f).exists

def test_service_started(host):
    assert host.service("mapr-zookeeper").is_running
    assert host.service("mapr-warden").is_running


def test_yarn_config_with_kerberos(host):
    vars = host.ansible.get_variables()
    f = host.file("/opt/mapr/hadoop/hadoop-2.7.0/etc/hadoop/yarn-site.xml")
    assert f.exists
    assert """
  <property>
    <name>yarn.resourcemanager.ha.custom-ha-enabled</name>
    <value>true</value>
    <description>MapR Zookeeper based RM Reconnect Enabled. If this is true, set the failover proxy to be the class MapRZKBasedRMFailoverProxyProvider</description>
  </property>
  <property>
    <name>yarn.client.failover-proxy-provider</name>
    <value>org.apache.hadoop.yarn.client.MapRZKBasedRMFailoverProxyProvider</value>
    <description>Zookeeper based reconnect proxy provider. Should be set if and only if mapr-ha-enabled property is true.</description>
  </property>
  <property>
    <name>yarn.resourcemanager.recovery.enabled</name>
    <value>true</value>
    <description>RM Recovery Enabled</description>
  </property>
  <property>
   <name>yarn.resourcemanager.ha.custom-ha-rmaddressfinder</name>
   <value>org.apache.hadoop.yarn.client.MapRZKBasedRMAddressFinder</value>
  </property>

  <property>
    <name>yarn.acl.enable</name>
    <value>true</value>
  </property>
  <property>
    <name>yarn.admin.acl</name>
    <value> </value>
  </property>

  <!-- :::CAUTION::: DO NOT EDIT ANYTHING ON OR ABOVE THIS LINE -->
    <!-- fix for Oozie when user different than mapr -->
    <property>
        <name>yarn.resourcemanager.principal</name>
        <value>mapr</value>
    </property>
    <property>
        <name>yarn.nodemanager.container-executor.class</name>
        <value>org.apache.hadoop.yarn.server.nodemanager.LinuxContainerExecutor</value>
    </property>
    <property>
        <name>yarn.nodemanager.linux-container-executor.group</name>
        <value>mapr</value>
    </property>
    <property>
        <name>yarn.log-aggregation-enable</name>
        <value>false</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-mb</name>
        <value>131072</value>
        <description>The maximum allocation for every container request at the RM, in MBs. Memory requests higher than this will throw a InvalidResourceRequestException.</description>
    </property>
    <property>
        <name>yarn.resourcemanager.am.max-attempts</name>
        <value>4</value>
        <description>The maximum number of application attempts</description>
    </property>
            <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle,mapr_direct_shuffle,spark_shuffle</value>
        <description>shuffle service that needs to be set for Map Reduce to run</description>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services.spark_shuffle.class</name>
        <value>org.apache.spark.network.yarn.YarnShuffleService</value>
    </property>
    <property>
        <name>spark.shuffle.service.port</name>
        <value>7337</value>
        <description>Port on which the external shuffle service will run.</description>
    </property>
        <property>
        <name>spark.authenticate</name>
        <value>true</value>
        <description>Whether Spark authenticates its internal connections.</description>
    </property>
        <property>
        <name>spark.yarn.shuffle.stopOnFailure</name>
        <value>false</value>
        <description>Whether to stop the NodeManager when there's a failure in the Spark Shuffle Service's initialization.
            This prevents application failures caused by running containers on NodeManagers where the Spark Shuffle Service is not running.
        </description>
    </property>""" in f.content

def test_hadoop_fs(host):
    cmd = host.run("echo rootpass | maprlogin password")
    assert "MapR credentials of user 'root' for cluster 'demo.mapr.com' are written to" in cmd.stdout
    cmd = host.run("hadoop fs -ls /")
    assert "Found 5 items" in cmd.stdout

def helper_test_yarn_application(host):
    pps = host.run("curl -u root:rootpass --cacert /opt/mapr/conf/ssl_truststore.pem -X GET -H \"Content-Type:application/json\" https://molecule-cluster:8090/ws/v1/cluster/apps")
    state = sorted(json.loads(apps.stdout)['apps']['app'], key=lambda k: k['startedTime'], reverse=True)[0]['finalStatus']
    assert state == "SUCCEEDED"

def test_yarn(host):
    host.run("/opt/mapr/hadoop/hadoop-2.7.0/bin/yarn jar /opt/mapr/hadoop/hadoop-2.7.0/share/hadoop/mapreduce/hadoop-mapreduce-examples-2.7.0-mapr-1808.jar pi 5 10")
    helper_test_yarn_application(host)

def test_hadoop(host):
    host.run("hadoop jar /opt/mapr/hadoop/hadoop-2.7.0/share/hadoop/mapreduce/hadoop-mapreduce-examples-2.7.0-mapr-1808.jar pi 5 10")
    helper_test_yarn_application(host)
