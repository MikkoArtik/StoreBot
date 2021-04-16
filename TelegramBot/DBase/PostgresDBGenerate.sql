create table Users
(
    id serial primary key,
    chat_id integer not null,
    reg_date timestamp not null,
    account_type varchar(20) default 'base'
);

create table Links
(
    id serial primary key,
    user_id int4 references Users(id) on delete cascade,
    store varchar(20) not null,
    link varchar(250) not null,
    reg_dt timestamp not null,
    target_price numeric(20,2) default 0,
    pre_price numeric(20, 2) default 10000000000,
    current_price numeric(20, 2) default 10000000000,
    status boolean default true
);