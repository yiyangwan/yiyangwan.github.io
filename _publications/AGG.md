---
title: "A Bayesian-Guided Aggregation-Disaggregation Algorithm for Transit Planning"
excerpt: "<p align='center'><a href='/publications/AGG'><img src='/images/AGG.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/AGG
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
date: 2021-10-19
venue: 'Working Paper'
# paperurl: 'https://ieeexplore.ieee.org/document/8684317'
# citation: 'Yiyang Wang, Neda Masoud. <i>Working Paper.</i>'
---

<!-- [[PDF]](https://www.researchgate.net/publication/345699783_Adversarial_Online_Learning_with_Variable_Plays_in_the_Pursuit-Evasion_Game_Theoretical_Foundations_and_Application_in_Connected_and_Automated_Vehicle_Cybersecurity)
[[CODE]](https://github.com/yiyang920/adversarial_multi_armed_bandit_variable_plays) -->

## Abstract
Public transit is essential for daily mobility, especially for individuals without access to private vehicles, yet designing efficient transit systems remains challenging when demand is spatially dispersed, density is low, and operational resources are constrained.
This paper introduces an integer programming model based on a many-to-many (M2M) matching framework that captures detailed routing decisions while accounting for vehicle capacity, transfer constraints, and user-perceived service quality. 
To address the scalability challenges of solving this model directly, we propose a hybrid solution approach that integrates Bayesian optimization (BO) with a structured aggregation-disaggregation procedure. 
In this solution framework, aggregation-disaggregation allows efficient evaluation of candidate network configurations, while BO guides the search over the space of network aggregations.
We evaluate this approach in a real-world case study using observations from Benton Harbor, Michigan. 
Experimental results show that our solution method improves solution quality by nearly a factor of two compared to solving the full M2M model directly, highlighting its potential for scalable and adaptive transit planning in resource-constrained environments.