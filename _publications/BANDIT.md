---
title: "Adversarial Online Learning with Variable Plays in the Pursuit-Evasion Game: Theoretical Foundations and Application in Connected and Automated Vehicle Cybersecurity"
excerpt: "<p align='center'><a href='/publications/BANDIT'><img src='/images/BANDIT.png' style='width: 500px;'></a></p>"
collection: publications
permalink: /publications/BANDIT
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2021-10-15
venue: 'IEEE Access'
paperurl: 'https://ieeexplore.ieee.org/abstract/document/9576732'
# citation: 'Yiyang Wang, Neda Masoud. &quot;Adversarial Online Learning with Variable Plays in the Pursuit-Evasion Game: Theoretical Foundations and Application in Connected and Automated Vehicle Cybersecurity.&quot; <i>In IEEE Access, vol. 9, pp. 142475-142488, 2021, doi: 10.1109/ACCESS.2021.3120700.</i>'
---

[[CODE]](https://github.com/wayiya/adversarial_multi_armed_bandit_variable_plays)
[[PDF]](/files/articles/BANDIT.pdf)


## Abstract
We extend the adversarial/non-stochastic multi-play multi-armed bandit (MPMAB) to the case where the number of arms to play is variable. The work is motivated by the fact that the resources allocated to scan different critical locations in an interconnected transportation system change dynamically over time and depending on the environment. By modeling the malicious hacker and the intrusion monitoring system as the attacker and the defender, respectively, we formulate the problem for the two players as a sequential pursuit-evasion game. We derive the condition under which a Nash equilibrium of the strategic game exists. For the defender side, we provide an exponential-weighted based algorithm with sublinear pseudo-regret. We further extend our model to heterogeneous rewards for both players, and obtain lower and upper bounds on the average reward for the attacker. We provide numerical experiments to demonstrate the effectiveness of a variable-arm play.

| ![](/images/BANDIT.png) |
|:--:|
| *A pursuit-evasion game scenario where a malicious attacker who adopts Exp3 compromises the red vehicle, and a security monitor as defender who adopts Exp3.M-VP scans the red vehicle as well as two other vehicles. The pursuit-evasion game is conducted in a sequential manner.* |
