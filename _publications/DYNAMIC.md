---
title: "A Dynamic Deep Reinforcement Learning-Bayesian Framework for Anomaly Detection"
excerpt: "<p align="center"><img src='/images/DYNAMIC.png' style='width: 500px;'></p>"
collection: publications
permalink: /publications/DYNAMIC
date: 2021-08-23
venue: 'IEEE Transactions on Intelligent Transportation Systems (under review)'
# paperurl: 'https://ieeexplore.ieee.org/document/8684317'
citation: 'Jeremy Watts, Franco van Wyk, Shahrbanoo Rezaei, Yiyang Wang, Anahita Khojandi, Neda Masoud. &quot;A Dynamic Deep Reinforcement Learning-Bayesian Framework for Anomaly Detection.&quot; <i>DOI: 10.13140/RG.2.2.35285.55526</i>'
---

[[PDF]](https://www.researchgate.net/publication/349376559_A_Dynamic_Deep_Reinforcement_Learning-Bayesian_Framework_for_Anomaly_Detection)


## Abstract
To assure the successful operation of connected and automated vehicles, it is critical to detect and isolate anomalous and/or faulty information in a timely manner. To do so, anomaly detection techniques should be implemented in real-time where if the probability of anomalous information exceeds a certain threshold, the information is dealt with accordingly. Traditionally, the threshold that determines if data are anomalous or not is fixed and determined a priori. However, not only does this approach fail to account for the feedback obtained during a trip on the performance of the algorithms, but it also fails to respond to potential changes in rates of anomalies. Hence, it is important to develop an approach that can dynamically alter this threshold in response to exogenous factors to assure reliable and robust system operation. We develop a mathematical framework to determine the optimal dynamic threshold of an anomaly classification algorithm in order to maximize the safety of a trip. Specifically, we develop and pair an anomaly classification algorithm based on convolutional neural networks (CNN), with a partially observable Markov decision process (POMDP) model. We solve the resulting POMDP model using the asynchronous advantage actor critic (A3C) deep reinforcement learning algorithm. The prescribed policy determines the optimal level of the anomaly classification threshold in real-time that maximizes the performance. Our numerical experiments show that the POMDP model outperforms state-of-the-art benchmarks, especially under more difficult to detect anomaly profiles.

![](/images/DYNAMIC.png)
<br/><i>Overview of the anomaly detection framework.</i>