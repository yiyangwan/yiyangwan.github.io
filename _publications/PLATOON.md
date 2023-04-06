---
title: "Anomaly Detection and String Stability Analysis in Connected Automated Vehicular Platoons"
excerpt: "<p align='center'><a href='/publications/PLATOON'><img src='/images/PLATOON.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/PLATOON
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2021-10-19
venue: 'Transportation Research Part C: Emerging Technologies'
paperurl: 'https://www.researchgate.net/publication/362382000_Anomaly_Detection_and_String_Stability_Analysis_in_Connected_Automated_Vehicular_Platoons'
citation: 'Yiyang Wang, Ruixuan Zhang, Neda Masoud, Henry X. Liu, "Anomaly detection and string stability analysis in connected automated vehicular platoons" <i>Transportation Research Part C: Emerging Technologies, Volume 151, 2023, 104114, ISSN 0968-090X, https://doi.org/10.1016/j.trc.2023.104114.</i>'
---

<!-- [[PDF]](https://www.researchgate.net/publication/345699783_Adversarial_Online_Learning_with_Variable_Plays_in_the_Pursuit-Evasion_Game_Theoretical_Foundations_and_Application_in_Connected_and_Automated_Vehicle_Cybersecurity)
[[CODE]](https://github.com/wayiya/adversarial_multi_armed_bandit_variable_plays) -->

## Abstract
In this study, we develop a comprehensive framework to model the impact of cyberattacks on safety, security, and head-to-tail stability of connected and automated vehicular platoons. First, we propose a general platoon dynamics model with heterogeneous time delays that may originate from the communication channel and/or vehicle onboard sensors. Based on the proposed dynamics model, we develop an augmented state extended Kalman filter (ASEKF) to smooth sensor readings, and use it in conjunction with an anomaly detector to detect sensor anomalies. Specifically, we consider two detectors: a parametric detector, the χ2-detector, and a learning-based detector, the one class support vector machine (OCSVM). We investigate the detection power of all combinations of vehicle dynamics models (EKF and ASEKF) and detectors (χ2 and OCSVM). Furthermore, we introduce a novel concept in string stability, namely, pseudo string stability, to measure a platoon’s string stability under cyberattacks and model uncertainties. We demonstrate the relationship between the pseudo string stability of a platoon and its detection rate, which enables us to identify the critical detection sensitivity/recall that the platoon’s members should meet for the platoon to remain pseudo string stable.

| ![](/images/PLATOON.png) |
|:--:|
| *An example of platoon with 3-predecessor following information flow topology and with cloud information.* |
