{% load i18n %}

<div id="task_main">
{% if submission %}
    <h1>{{ submission }}</h1>
{% endif %}

{# this form needs an explicit action, because it is used in widgets #}
<form id="{{ form_id }}" action="{% url ecs.tasks.views.my_tasks %}" method="post" class="open-in-widget">
    <div class="task_list_choose">
        <label class="task_sorting">{% trans "Sort by" %}:</label> {{ filterform.sorting }}
    </div>
    <ul class="task_list_choose">
        {{ filterform.mine }} <li><label for="id_mine"><span class="task_mine"></span>{% trans "Mine" %}</label></li>
        {{ filterform.assigned }} <li><label for="id_assigned"><span class="task_assigned"></span>{% trans "Assigned" %}</label></li>
        {{ filterform.open }} <li><label for="id_open"><span class="task_open"></span>{% trans "Open" %}</label></li>
        {{ filterform.proxy }} <li><label for="id_proxy"><span class="task_proxy"></span>{% trans "Proxy" %}</label></li>
    </ul>
    <ul class="task_list_choose"{% if submission %} style="display:none"{% endif %}>
        {{ filterform.amg }} <li><label for="id_amg"><span class="task_amg"></span>{% trans "AMG" %}</label></li>
        {{ filterform.mpg }} <li><label for="id_mpg"><span class="task_mpg"></span>{% trans "MPG" %}</label></li>
        {{ filterform.thesis }} <li><label for="id_thesis"><span class="task_thesis"></span>{% trans "thesis" %}</label></li>
        {{ filterform.other }} <li><label for="id_other"><span class="task_other"></span>{% trans "Other" %}</label></li>
    </ul>
</form>

{% if mine_tasks %}
    <div class="task_list">
        <h2>{% trans "My Tasks" %}</h2>
        {% regroup mine_tasks by task_type as task_type_list %}
        {% for task_type in task_type_list %}
            <div class="task_item{% if task_type.list|length > 3 %} toggle_collapse{% endif %}">
                <h3>({{ task_type.list|length }}) {{ task_type.grouper }}</h3>
                <ul> {% for task in task_type.list %} <li>
                    {% url ecs.tasks.views.manage_task task_pk=task.pk as manage_url %}
                    <a href="{{ task.url|default:manage_url }}" class="{% if not task.url %}open-in-popup{% endif %}">{{ task.data }}</a>{% if not forloop.last %},{% endif %}
                </li> {% endfor %} </ul>
                <div style="clear:both;"></div>
            </div>
        {% endfor %}
    </div>
{% endif %}

{% if assigned_tasks %}
    <div class="task_list">
        <h2>{% trans "Tasks assigned to me" %}</h2>
        {% regroup assigned_tasks by task_type as task_type_list %}
        {% for task_type in task_type_list %}
            <div class="task_item{% if task_type.list|length > 3 %} toggle_collapse{% endif %}">
                <h3>({{ task_type.list|length }}) {{ task_type.grouper }}</h3>
                <ul> {% for task in task_type.list %} <li>
                    <a class="open-in-widget" href="{% url ecs.tasks.views.accept_task task_pk=task.pk %}">{{ task.data }}</a>
                    <a href="{{ task.get_preview_url }}">{% trans "Preview" %}</a>
                    | <a class="open-in-widget" href="{% url ecs.tasks.views.decline_task task_pk=task.pk %}">{% trans "Decline" %}</a>{% if not forloop.last %}, {% endif %}
                </li> {% endfor %} </ul>
                <div style="clear:both;"></div>
            </div>
        {% endfor %}
    </div>
{% endif %}

{% if open_tasks %}
    <div class="task_list">
        <h2>{% trans "Open Tasks" %}</h2>
        {% regroup open_tasks by task_type as task_type_list %}
        {% for task_type in task_type_list %}
            <div class="task_item{% if task_type.list|length > 3 %} toggle_collapse{% endif %}">
                <h3>({{ task_type.list|length }}) {{ task_type.grouper }}</h3>
                <ul> {% for task in task_type.list %} <li>
                    <a class="open-in-widget" href="{% url ecs.tasks.views.accept_task task_pk=task.pk %}">{{ task.data }}</a>
                    <a href="{{ task.get_preview_url }}">{% trans "Preview" %}</a>{% if not forloop.last %}, {% endif %}
                </li> {% endfor %} </ul>
                <div style="clear:both;"></div>
            </div>
        {% endfor %}
    </div>
{% endif %}

{% if proxy_tasks %}
    <div class="task_list">
        <h2>{% trans "Proxy Tasks" %}</h2>
        {% regroup proxy_tasks by task_type as task_type_list %}
        {% for task_type in task_type_list %}
            <div class="task_item{% if task_type.list|length > 3 %} toggle_collapse{% endif %}">
                <h3>({{ task_type.list|length }}) {{ task_type.grouper }}</h3>
                <ul> {% for task in task_type.list %} <li>
                    <a class="open-in-widget" href="{% url ecs.tasks.views.accept_task task_pk=task.pk %}">{{ task.data }}</a>
                    <a href="{{ task.get_preview_url }}">{% trans "Preview" %}</a>{% if not forloop.last %}, {% endif %}
                </li> {% endfor %} </ul>
                <div style="clear:both;"></div>
            </div>
        {% endfor %}
    </div>
{% endif %}

{% if not mine_tasks and not assigned_tasks and not open_tasks and not proxy_tasks %}
    <em>{% trans "There are no tasks for you." %}</em>
{% endif %}
</div>

