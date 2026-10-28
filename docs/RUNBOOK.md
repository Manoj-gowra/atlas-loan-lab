# Atlas case-file assistant: operations runbook

Owner: TODO · Update trigger: TODO
Course link: lesson 6.3 (operational guidance), with 3.6 (alerts), 5.1 (fail secure) and 5.2 (queues).

<!--
LAB 6 TODO (lesson 6.3). Someone who was never in the room must be able to run the system from this page.
Write it from the code, not from memory - the tests read the code and check this file against it:

1. Owner and update trigger: who keeps this page current, and WHICH EVENT forces an update (the same
   events that change the system: alerts, triggers, queues, policy documents, the index build).
2. Section "Alerts": one table row per alert id in atlas/monitoring.py ALERTS (use the exact id in
   backticks): what it means (which failure mode), the first response, who is paged.
3. Section "Escalation triggers": one table row per trigger in atlas/escalation.py TRIGGERS with its
   queue name AND role from QUEUES (exact names, in backticks), and what the reviewer does.
4. Section "Failure modes that are correct behaviour": at least the authorization service outage. Say
   that a denial during an outage is treated as a DENIAL to investigate, not a bug to route around.
5. Routine operations: what to do on a policy update (hint: the index) and on a prompt/model change.
Delete this comment and every TODO when you are done.
-->

## 1. Alerts

| Alert id | What it means | First response | Who is paged |
|---|---|---|---|
| TODO | | | |

## 2. Escalation triggers

| Trigger | Queue | Role | What the reviewer does |
|---|---|---|---|
| TODO | | | |

## 3. Failure modes that are correct behaviour

TODO

## 4. Routine operations

TODO
