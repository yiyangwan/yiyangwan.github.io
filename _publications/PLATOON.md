---
title: "Anomaly Detection and String Stability Analysis in Connected Automated Vehicular Platoons"
excerpt: "<p align='center'><a href='/publications/RSU'><img src='/images/PLATOON.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/PLATOON
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2021-10-19
venue: 'Working Paper'
# paperurl: 'https://ieeexplore.ieee.org/document/8684317'
# citation: 'Yiyang Wang, Neda Masoud. <i>Working Paper.</i>'
---

<!-- [[PDF]](https://www.researchgate.net/publication/345699783_Adversarial_Online_Learning_with_Variable_Plays_in_the_Pursuit-Evasion_Game_Theoretical_Foundations_and_Application_in_Connected_and_Automated_Vehicle_Cybersecurity)
[[CODE]](https://github.com/yiyang920/adversarial_multi_armed_bandit_variable_plays) -->

## Abstract
In this study, we develop a comprehensive framework to model the impact of cyberattacks on safety, security, and head-to-tail stability of connected and automated vehicular platoons. First, we propose a general platoon dynamics model with heterogeneous time delays that may originate from the communication channel and/or vehicle onboard sensors. Based on the proposed dynamics model, we develop an augmented state extended Kalman filter (ASEKF) to smooth the sensor reading, and use it in conjunction with an anomaly detector to detect sensor anomalies. Specifically, we consider two detectors: a parametric detector, the $\chi^2$-detector, and a learning-based detector, the one class support vector machine (OCSVM). We investigate the detection power of all combinations of vehicle dynamics models (EKF and ASEKF) and detectors ($\chi^2$ and OCSVM). Furthermore, we introduce a novel concept in string stability, namely, pseudo string stability, to measure a platoon's string stability under cyberattacks and model uncertainties. We demonstrate the relationship between the pseudo string stability of a platoon and its detection rate, which enables us to identity the critical detection sensitivity/recall that the platoon's members should posses for the platoon to remain pseudo string stable.