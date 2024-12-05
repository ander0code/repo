create table achievements
(
    id          bigserial
        primary key,
    name        text,
    description text,
    unlock      text
);

create table auth_group
(
    id   integer generated by default as identity
        primary key,
    name varchar(150) not null
        unique
);

create index auth_group_name_a6ea08ec_like
    on auth_group (name varchar_pattern_ops);

create table auth_user
(
    id           integer generated by default as identity
        primary key,
    password     varchar(128)             not null,
    last_login   timestamp with time zone,
    is_superuser boolean                  not null,
    username     varchar(150)             not null
        unique,
    first_name   varchar(150)             not null,
    last_name    varchar(150)             not null,
    email        varchar(254)             not null,
    is_staff     boolean                  not null,
    is_active    boolean                  not null,
    date_joined  timestamp with time zone not null
);


create index auth_user_username_6821ab7c_like
    on auth_user (username varchar_pattern_ops);

create table auth_user_groups
(
    id       bigint generated by default as identity
        primary key,
    user_id  integer not null
        constraint auth_user_groups_user_id_6a12ed8b_fk_auth_user_id
            references auth_user
            deferrable initially deferred,
    group_id integer not null
        constraint auth_user_groups_group_id_97559544_fk_auth_group_id
            references auth_group
            deferrable initially deferred,
    constraint auth_user_groups_user_id_group_id_94350c0c_uniq
        unique (user_id, group_id)
);


create index auth_user_groups_group_id_97559544
    on auth_user_groups (group_id);

create index auth_user_groups_user_id_6a12ed8b
    on auth_user_groups (user_id);

create table authtoken_token
(
    key     varchar(40)              not null
        primary key,
    created timestamp with time zone not null,
    user_id integer                  not null
        unique
        constraint authtoken_token_user_id_35299eff_fk_auth_user_id
            references auth_user
            deferrable initially deferred
);


create index authtoken_token_key_10f0b77e_like
    on authtoken_token (key varchar_pattern_ops);

create table django_content_type
(
    id        integer generated by default as identity
        primary key,
    app_label varchar(100) not null,
    model     varchar(100) not null,
    constraint django_content_type_app_label_model_76bd3d3b_uniq
        unique (app_label, model)
);


create table auth_permission
(
    id              integer generated by default as identity
        primary key,
    name            varchar(255) not null,
    content_type_id integer      not null
        constraint auth_permission_content_type_id_2f476e4b_fk_django_co
            references django_content_type
            deferrable initially deferred,
    codename        varchar(100) not null,
    constraint auth_permission_content_type_id_codename_01ab375a_uniq
        unique (content_type_id, codename)
);


create table auth_group_permissions
(
    id            bigint generated by default as identity
        primary key,
    group_id      integer not null
        constraint auth_group_permissions_group_id_b120cbf9_fk_auth_group_id
            references auth_group
            deferrable initially deferred,
    permission_id integer not null
        constraint auth_group_permissio_permission_id_84c5c92e_fk_auth_perm
            references auth_permission
            deferrable initially deferred,
    constraint auth_group_permissions_group_id_permission_id_0cd325b0_uniq
        unique (group_id, permission_id)
);


create index auth_group_permissions_group_id_b120cbf9
    on auth_group_permissions (group_id);

create index auth_group_permissions_permission_id_84c5c92e
    on auth_group_permissions (permission_id);

create index auth_permission_content_type_id_2f476e4b
    on auth_permission (content_type_id);

create table auth_user_user_permissions
(
    id            bigint generated by default as identity
        primary key,
    user_id       integer not null
        constraint auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id
            references auth_user
            deferrable initially deferred,
    permission_id integer not null
        constraint auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm
            references auth_permission
            deferrable initially deferred,
    constraint auth_user_user_permissions_user_id_permission_id_14a6b632_uniq
        unique (user_id, permission_id)
);

create index auth_user_user_permissions_permission_id_1fbb5f2c
    on auth_user_user_permissions (permission_id);

create index auth_user_user_permissions_user_id_a95ead1b
    on auth_user_user_permissions (user_id);

create table django_admin_log
(
    id              integer generated by default as identity
        primary key,
    action_time     timestamp with time zone not null,
    object_id       text,
    object_repr     varchar(200)             not null,
    action_flag     smallint                 not null
        constraint django_admin_log_action_flag_check
            check (action_flag >= 0),
    change_message  text                     not null,
    content_type_id integer
        constraint django_admin_log_content_type_id_c4bce8eb_fk_django_co
            references django_content_type
            deferrable initially deferred,
    user_id         integer                  not null
        constraint django_admin_log_user_id_c564eba6_fk_auth_user_id
            references auth_user
            deferrable initially deferred
);

create index django_admin_log_content_type_id_c4bce8eb
    on django_admin_log (content_type_id);

create index django_admin_log_user_id_c564eba6
    on django_admin_log (user_id);

create table django_migrations
(
    id      bigint generated by default as identity
        primary key,
    app     varchar(255)             not null,
    name    varchar(255)             not null,
    applied timestamp with time zone not null
);


create table django_session
(
    session_key  varchar(40)              not null
        primary key,
    session_data text                     not null,
    expire_date  timestamp with time zone not null
);


create index django_session_expire_date_a5c62663
    on django_session (expire_date);

create index django_session_session_key_c0390e0f_like
    on django_session (session_key varchar_pattern_ops);

create table tags
(
    id          bigserial
        primary key,
    name        text not null,
    search_date timestamp default CURRENT_TIMESTAMP,
    counter     integer   default 0
);

create table users
(
    id                    bigserial
        primary key,
    university            text,
    career                text,
    cycle                 text,
    biography             text,
    photo                 text,
    achievements          text,
    created_at            timestamp default CURRENT_TIMESTAMP,
    authuser_id           integer
        constraint fk_auth_user
            references auth_user
            on delete cascade,
    reset_code            integer,
    reset_code_created_at timestamp,
    interests             character varying[]
);

create table forms
(
    id          bigserial
        primary key,
    title       text,
    url         text,
    created_at  timestamp default CURRENT_TIMESTAMP,
    created_end timestamp default CURRENT_TIMESTAMP,
    user_id     integer
        constraint fk_users_forms
            references users
);

create table notifications
(
    id         bigserial
        primary key,
    sender_id  bigint
        constraint fk_user_notification
            references users
            on delete cascade,
    message    text,
    is_read    integer,
    created_at timestamp default CURRENT_TIMESTAMP,
    user_id    integer
);

create table projects
(
    id                     bigserial
        primary key,
    name                   text,
    description            text,
    start_date             date    default CURRENT_TIMESTAMP,
    end_date               date    default CURRENT_TIMESTAMP,
    status                 text,
    priority               text,
    responsible            bigint
        constraint fk_responsible
            references users
            on update cascade on delete set null,
    detailed_description   text,
    progress               integer,
    accepting_applications boolean default true,
    type_aplyuni           text,
    name_uniuser           text,
    objectives             text[],
    necessary_requirements text[],
    project_type           character varying[]
);


create table collaborations
(
    id      bigserial
        primary key,
    user_id bigint
        constraint fk_user_collaboration
            references users
            on delete cascade,
    project bigint
        constraint fk_project_collaboration
            references projects
            on delete cascade,
    role    text,
    status  text default 'Pendiente'::text not null
);

create table solicitudes
(
    id_solicitud serial
        primary key,
    id_user      bigint
        references users
            on delete cascade,
    id_project   bigint
        references projects
            on delete cascade,
    status       text default 'Pendiente'::text not null,
    created_at   timestamp,
    name_user    text,
    name_lider   text,
    name_project text,
    message      text,
    photo        text
);

create table tag_associations
(
    id         bigserial
        primary key,
    tag_id     bigint
        constraint fk_tag
            references tags
            on update cascade on delete cascade,
    project_id bigint
        constraint fk_project
            references projects
            on update cascade on delete cascade
);

create table user_achievements
(
    id             bigserial
        primary key,
    user_id        bigint
        constraint fk_user
            references users,
    achievement_id bigint
        constraint fk_achievement
            references achievements,
    unlocked       boolean not null
);


