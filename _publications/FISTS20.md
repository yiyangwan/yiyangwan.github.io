---
title: "Anomaly Detection in Connected and Automated Vehicles using an Augmented State Formulation"
excerpt: "<p align='center'><a href='/publications/FISTS20'><img src='/images/FISTS20.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/FISTS20
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2020-11-24
venue: '2020 IEEE Forum on Integrated and Sustainable Transportation Systems (FISTS)'
paperurl: 'https://ieeexplore.ieee.org/document/9264885'
# citation: 'Yiyang Wang, Neda Masoud, and Anahita Khojandi. &quot;Anomaly Detection in Connected and Automated Vehicles using an Augmented State Formulation.&quot; <i>In 2020 Forum on Integrated and Sustainable Transportation Systems (FISTS), pp. 156-161. IEEE, 2020.</i>'
---

[[CODE]](https://github.com/wayiya/CF_Anomaly_Detection)
[[PDF]](https://wayiya.github.io/files/articles/FISTS20.pdf)


## Abstract
In this paper we propose a novel observer-based method for anomaly detection in connected and automated vehicles (CAVs). The proposed method utilizes an augmented extended Kalman filter (AEKF) to smooth sensor readings of a CAV based on a nonlinear car-following motion model with time delay, where the leading vehicle's trajectory is used by the subject vehicle to detect sensor anomalies. We use the classic $\chi^2$-fault detector in conjunction with the proposed AEKF for anomaly detection. To make the proposed model more suitable for real-world applications, we consider a stochastic communication time delay in the car-following model. Our experiments conducted on real-world connected vehicle data indicate that the AEKF with $\chi^2$-detector can achieve a high anomaly detection performance.

| ![](/images/FISTS20.png) |
|:--:|
| *Example of a normalized innovation sequence being non-zero mean. Left: scatter plot of EKF. Right: scatter plot of AEKF.* |
