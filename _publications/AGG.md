---
title: "A Bayesian-Guided Aggregation-Disaggregation Algorithm for Transit Planning"
excerpt: "<p align='center'><a href='/publications/AGG'><img src='/images/AGG.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/AGG
# excerpt: 'This paper is about the number 1. The number 2 is left for future work.'
# Kept at/before today: _config.yml sets `future: false`, so a future date would
# drop this page from the build and 404 the link on /publications/.
date: 2026-08-05
venue: 'Bridging Transportation Researchers (BTR8) Conference'
paperurl: 'https://www.researchgate.net/profile/Jisoon-Lim/publication/400258414_A_Bayesian-Guided_Aggregation-Disaggregation_Algorithm_for_Transit_Planning/links/697cfb4a12f837212a166204/A-Bayesian-Guided-Aggregation-Disaggregation-Algorithm-for-Transit-Planning.pdf'
# citation: 'Golbarg Dokhani, Jisoon Lim, Neda Masoud, Yiyang Wang, Amirmahdi Tafreshian. <i>Bridging Transportation Researchers (BTR8) Conference.</i>'
---

[[PDF]](https://www.researchgate.net/profile/Jisoon-Lim/publication/400258414_A_Bayesian-Guided_Aggregation-Disaggregation_Algorithm_for_Transit_Planning/links/697cfb4a12f837212a166204/A-Bayesian-Guided-Aggregation-Disaggregation-Algorithm-for-Transit-Planning.pdf)

Presented at the [Bridging Transportation Researchers (BTR8) Conference](https://bridgingtransport.org/btr-program/), Session W8: Public Transit Planning & Operations, August 13, 2026 (virtual).

## Abstract
Public transit is essential for daily mobility, especially for individuals without access to private vehicles, yet designing efficient transit systems remains challenging when demand is spatially dispersed, density is low, and operational resources are constrained.
This paper introduces an integer programming model based on a many-to-many (M2M) matching framework that captures detailed routing decisions while accounting for vehicle capacity, transfer constraints, and user-perceived service quality. 
To address the scalability challenges of solving this model directly, we propose a hybrid solution approach that integrates Bayesian optimization (BO) with a structured aggregation-disaggregation procedure. 
In this solution framework, aggregation-disaggregation allows efficient evaluation of candidate network configurations, while BO guides the search over the space of network aggregations.
We evaluate this approach in a real-world case study using observations from Benton Harbor, Michigan. 
Experimental results show that our solution method improves solution quality by nearly a factor of two compared to solving the full M2M model directly, highlighting its potential for scalable and adaptive transit planning in resource-constrained environments.