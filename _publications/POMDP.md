---
title: "Dynamic Security Resource Allocation for Connected and Automated Vehicles"
excerpt: "<p align='center'><a href='/publications/POMDP'><img src='/images/POMDP.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/POMDP
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2022-9-1
venue: 'Working Paper'
# paperurl: 'https://www.researchgate.net/publication/362382000_Anomaly_Detection_and_String_Stability_Analysis_in_Connected_Automated_Vehicular_Platoons'
# citation: 'Wang, Yiyang, et al. "Anomaly detection and string stability analysis in connected automated vehicular platoons." <i>Transportation Research Part C: Emerging Technologies 151 (2023): 104114.</i>'
---

<!-- [[PDF]](https://www.researchgate.net/publication/345699783_Adversarial_Online_Learning_with_Variable_Plays_in_the_Pursuit-Evasion_Game_Theoretical_Foundations_and_Application_in_Connected_and_Automated_Vehicle_Cybersecurity)
[[CODE]](https://github.com/wayiya/adversarial_multi_armed_bandit_variable_plays) -->

## Abstract
In this study, we address the dynamic security resource allocation for a CAV through sequential decision making under uncertainty and partial information. Specifically, we consider a CAV driving on a planned route and subject to potential cyberattacks. The true status of cyberattacks can only be observed via an attack detection monitor deployed on the CAV or on the cloud. The amount of security resources that can be allocated for monitoring depends on the energy supply of the CAV. At each time epoch, the CAV decides the amount of security resource to be allocated for attack detection. We assume that the detection recall/sensitivity is a function of the amount of allocated security resource. We further associate costs to undetected attacks and an unfinished trip due to energy depletion. As such, there is a trade-off between monitoring the CAV system to improve the detection sensitivity, and the risk of being unable to finish the trip. We develop a partially observable Markov decision process (POMDP) model that captures this trade-off by prescribing a security resource allocation policy to minimize the total discounted cost of a CAV trip over a finite horizon. To the best of our knowledge, it is the first study addressing the aforementioned trade-off and devising a dynamic security resource allocation policy for CAVs.

| ![](/images/POMDP.png) |
|:--:|
| *POMDP diagram for the security resource allocation problem.* |
