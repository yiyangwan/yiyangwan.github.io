---
title: "Dynamic Security Resource Allocation for Connected and Automated Vehicles"
excerpt: "<p align='center'><a href='/publications/POMDP'><img src='/images/POMDP.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/POMDP
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2022-9-1
venue: 'Under Review'
# paperurl: 'https://www.researchgate.net/publication/362382000_Anomaly_Detection_and_String_Stability_Analysis_in_Connected_Automated_Vehicular_Platoons'
# citation: 'Wang, Yiyang, et al. "Anomaly detection and string stability analysis in connected automated vehicular platoons." <i>Transportation Research Part C: Emerging Technologies 151 (2023): 104114.</i>'
---

<!-- [[PDF]](https://www.researchgate.net/publication/345699783_Adversarial_Online_Learning_with_Variable_Plays_in_the_Pursuit-Evasion_Game_Theoretical_Foundations_and_Application_in_Connected_and_Automated_Vehicle_Cybersecurity)
[[CODE]](https://github.com/wayiya/adversarial_multi_armed_bandit_variable_plays) -->

## Abstract
This paper presents a framework for dynamic security resource allocation in Connected and Automated Vehicles (CAVs), focusing on the challenge of cybersecurity amidst resource limitations. Given that CAVs rely on finite energy supplies for various essential functions—such as propulsion, sensing, computing, and security monitoring—we address the trade-offs involved in allocating resources to an onboard security monitor in the face of potential cyberattacks. A key challenge is the imperfect detection of attacks, where the CAV’s security system can only partially observe the attack state through a detection algorithm. To address this, we formulate the problem as a Partially Observable Markov Decision Process (POMDP), aimed at minimizing the total discounted cost over a finite horizon by dynamically allocating security resources, ensuring both safety and successful trip completion. Additionally, we propose a Q-learning-based approach for approximating optimal policies in large-scale systems. Through numerical experiments, we demonstrate the effectiveness of our approach in both small and large-scale settings, comparing it with benchmark policies. Our results show that the proposed framework successfully balances security monitoring and energy efficiency, with the Q-learning approach offering a scalable solution for larger systems. This work provides a novel contribution to security-aware resource allocation in CAVs, with implications for future transportation systems.

| ![](/images/POMDP.png) |
|:--:|
| *POMDP diagram for the security resource allocation problem.* |
