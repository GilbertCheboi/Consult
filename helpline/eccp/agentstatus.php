#!/usr/bin/php
<?php
require_once ("libs/ECCP.class.php");

if (count($argv) < 3) die("Use: {$argv[0]} agentchannel host\n");
$agentname = $argv[1];
$host = $argv[2];

$x = new ECCP();
try {
	$cr = $x->connect($host, "agentconsole", "agentconsole");
	if (isset($cr->failure)) die('Failed to connect to ECCP - '.$cr->failure->message."\n");
	$x->setAgentNumber($agentname);
	print_r(json_encode($x->getAgentStatus()));
	$x->disconnect();
} catch (Exception $e) {
	print_r($e);
	print_r($x->getParseError());
}
?>
