---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---
You can also find my articles on [<b>my Google Scholar profile</b>](https://scholar.google.com/citations?user=uAL9f8kAAAAJ&hl=en).


{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}