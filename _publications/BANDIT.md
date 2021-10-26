---
title: "Adversarial Online Learning with Variable Plays in the Pursuit-Evasion Game: Theoretical Foundations and Application in Connected and Automated Vehicle Cybersecurity"
excerpt: "<p align='center'><img src='/images/BANDIT.png' style='width: 500px;'></p>"
collection: publications
permalink: /publications/BANDIT
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2021-10-15
venue: 'IEEE Access'
# paperurl: 'https://ieeexplore.ieee.org/document/8684317'
citation: 'Yiyang Wang, Neda Masoud. &quot;Adversarial Online Learning with Variable Plays in the Pursuit-Evasion Game: Theoretical Foundations and Application in Connected and Automated Vehicle Cybersecurity.&quot; <i>DOI
10.1109/ACCESS.2021.3120700, IEEE Access.</i>'
---

[[PDF]](https://github.com/yiyang920/files/articles/BANDIT.pdf)
[[CODE]](https://github.com/yiyang920/adversarial_multi_armed_bandit_variable_plays)

## Abstract
We extend the adversarial/non-stochastic multi-play multi-armed bandit (MPMAB) to the case where the number of arms to play is variable. The work is motivated by the fact that the resources allocated to scan different critical locations in an interconnected transportation system change dynamically over time and depending on the environment. By modeling the malicious hacker and the intrusion monitoring system as the attacker and the defender, respectively, we formulate the problem for the two players as a sequential pursuit-evasion game. We derive the condition under which a Nash equilibrium of the strategic game exists. For the defender side, we provide an exponential-weighted based algorithm with sublinear pseudo-regret. We further extend our model to heterogeneous rewards for both players, and obtain lower and upper bounds on the average reward for the attacker. We provide numerical experiments to demonstrate the effectiveness of a variable-arm play.

| ![](/images/BANDIT.png) |
|:--:|
| *A pursuit-evasion game scenario where a malicious attacker who adopts Exp3 compromises the red vehicle, and a security monitor as defender who adopts Exp3.M-VP scans the red vehicle as well as two other vehicles. The pursuit-evasion game is conducted in a sequential manner.* |