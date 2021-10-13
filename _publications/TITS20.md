---
title: "Real-Time Sensor Anomaly Detection and Recovery in Connected Automated Vehicle Sensors"
excerpt: "<img src='/images/TITS20.jpg' style='width: 450px;'/>"
collection: publications
permalink: /publications/TITS20
# excerpt: 'This paper is about the number 3. The number 4 is left for future work.'
date: 2020-02-05
venue: 'IEEE Transactions on Intelligent Transportation Systems 22.3 (2020): 1411-1421.'
# paperurl: 'http://academicpages.github.io/files/paper3.pdf'
citation: 'Yiyang Wang, Neda Masoud, and Anahita Khojandi. &quot;Real-Time Sensor Anomaly Detection and Recovery in Connected Automated Vehicle Sensors.&quot; <i>IEEE Transactions on Intelligent Transportation Systems 22.3 (2020): 1411-1421.</i>'
---


[[PDF]](https://arxiv.org/pdf/1911.01531.pdf)
[[CODE]](https://github.com/yiyang920/CF_Anomaly_Detection)

## Abstract
In this paper we propose a novel observer-based method to improve the safety and security of connected and automated vehicle (CAV) transportation. The proposed method combines model-based signal filtering and anomaly detection methods. Specifically, we use adaptive extended Kalman filter (AEKF) to smooth sensor readings of a CAV based on a nonlinear car-following model. Using the car-following model the subject vehicle (i.e., the following vehicle) utilizes the leading vehicle's information to detect sensor anomalies by employing previously-trained One Class Support Vector Machine (OCSVM) models. This approach allows the AEKF to estimate the state of a vehicle not only based on the vehicle's location and speed, but also by taking into account the state of the surrounding traffic. A communication time delay factor is considered in the car-following model to make it more suitable for real-world applications. Our experiments show that compared with the AEKF with a traditional $\chi^2$-detector, our proposed method achieves a better anomaly detection performance. We also demonstrate that a larger time delay factor has a negative impact on the overall detection performance.

![](/images/TITS20.jpg)
<br/><i>Implementation flowchart of the proposed algorithm.</i>