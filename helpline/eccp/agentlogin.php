#!/usr/bin/php
<?php

require_once ("libs/ECCP.class.php");

require_once __DIR__ . '/vendor/autoload.php';

use WebSocket\Client;



if (count($argv) < 5) die("Use: {$argv[0]} agentchannel agentpassword extension host\n");
$agentname = $argv[1];
$agentpass = $argv[2];
$extension = $argv[3];
$agenthost = $argv[4];


$x = new ECCP();
try {
    // Specify the WebSocket server URL
    $serverUrl = 'wss://chat.callcenter.africa/ws/chat/'.$extension.'/';
    // Connect to the WebSocket server
    $client = new Client($serverUrl);
    print "Connect...\n";
    $data = json_encode([
        'message' => [
            "content"=> "Connecting",
            'description' => "Connecting to ECCP ".$agenthost,
            'level' => "info"
        ]
    ]);
    $client->send($data);

	$cr = $x->connect($agenthost, "agentconsole", "agentconsole");
    if (isset($cr->failure)) {
        $data = json_encode([
            'message' => [
                "content"=> "Failed to connect to ECCP",
                'description' => 'Failed to connect to ECCP - '.$cr->failure->message,
                'level' => "error"
            ]
        ]);
        $client->send($data);
        die('Failed to connect to ECCP - '.$cr->failure->message."\n");
    }
    $x->setAgentNumber($agentname);
    $x->setAgentPass($agentpass);

    print "Login agent\n";

    $data = json_encode([
        'message' => [
            "content"=> "Login agent",
            'description' => 'Login in agent',
            'level' => "info"
        ]
    ]);
    $client->send($data);

    $json = json_encode($x->getAgentStatus());
    $data = json_encode([
        'message' => [
            "content"=> $json,
            'description' => 'Agent status '.$x->getAgentStatus(),
            'level' => "info"
        ]
    ]);
    $client->send($data);

    print_r($x->getAgentStatus());

	$r = $x->loginagent($argv[3]);
    print_r($r);

    $json = json_encode($r);
    $data = json_encode([
        'message' => [
            "content"=> $json,
            'description' => 'Agent login status '.$x->getAgentStatus(),
            'level' => "info"
        ]
    ]);
    $client->send($data);

	$bFalloLogin = FALSE;
	if (!isset($r->failure) && !isset($r->loginagent_response->failure)) while (!$bFalloLogin) {
		$x->wait_response(1);
		while ($e = $x->getEvent()) {
            print_r($e);

            $data = json_encode([
                'message' => [
                    "content"=> json_encode($e),
                    'description' => json_encode($e),
                    'level' => "success"
                ]
            ]);
            $client->send($data);

            foreach ($e->children() as $ee) $evt = $ee;
            if ($evt->getName() == 'agentfailedlogin') {
                $bFalloLogin = TRUE;

                $data = json_encode([
                    'message' => [
                        "content"=> "Agent login failed".$evt,
                        'description' => 'Agent login failed'.$evt,
                        'level' => "error"
                    ]
                ]);
                $client->send($data);

                break;
			}
		}
	}
    print "Disconnect...\n";

    $data = json_encode([
        'message' => [
            "content"=> "Disconnecting...",
            'description' => "Disconnecting from server",
            'level' => "warning"
        ]
    ]);
    $client->send($data);

	$x->disconnect();
} catch (Exception $e) {
	print_r($e);
    print_r($x->getParseError());
    $data = json_encode([
        'message' => [
            "content"=> "Error connecting to server",
            'description' => $e,
            'level' => "error"
        ]
    ]);
    $client->send($data);

}
    $client->close();
?>
