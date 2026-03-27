create extension if not exists pgcrypto;

do $$
begin
    if not exists (
        select 1
        from pg_type
        where typname = 'post_status'
    ) then
        create type post_status as enum ('Draft', 'Scheduled', 'Published');
    end if;
end $$;

create table if not exists public.user_credentials (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    fb_page_token text,
    telegram_bot_token text,
    telegram_chat_id text,
    gemini_system_prompt text not null default '',
    target_word_count integer not null default 800,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint user_credentials_user_id_unique unique (user_id),
    constraint user_credentials_target_word_count_check check (target_word_count > 0)
);

create table if not exists public.connected_channels (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    youtube_channel_id text not null,
    daily_quota integer not null default 5,
    today_processed_count integer not null default 0,
    quota_reset_date date not null default current_date,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint connected_channels_daily_quota_check check (daily_quota >= 0),
    constraint connected_channels_today_processed_count_check check (today_processed_count >= 0),
    constraint connected_channels_user_channel_unique unique (user_id, youtube_channel_id)
);

create table if not exists public.posts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    channel_id uuid not null references public.connected_channels(id) on delete cascade,
    source_video_id text,
    original_transcript text,
    cleaned_article text,
    thumbnail_url text,
    status post_status not null default 'Draft',
    facebook_publish_status text not null default 'Pending'
        check (facebook_publish_status in ('Pending', 'Published', 'Failed', 'Skipped')),
    telegram_publish_status text not null default 'Pending'
        check (telegram_publish_status in ('Pending', 'Published', 'Failed', 'Skipped')),
    schedule_time timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);



alter table if exists public.user_credentials
    add column if not exists telegram_chat_id text;

alter table if exists public.connected_channels
    add column if not exists quota_reset_date date not null default current_date;

alter table if exists public.posts
    add column if not exists source_video_id text,
    add column if not exists facebook_publish_status text not null default 'Pending',
    add column if not exists telegram_publish_status text not null default 'Pending';

alter table if exists public.posts
    add constraint if not exists posts_facebook_publish_status_check
        check (facebook_publish_status in ('Pending', 'Published', 'Failed', 'Skipped')),
    add constraint if not exists posts_telegram_publish_status_check
        check (telegram_publish_status in ('Pending', 'Published', 'Failed', 'Skipped'));

create index if not exists idx_connected_channels_user_id on public.connected_channels (user_id);
create index if not exists idx_connected_channels_youtube_channel_id on public.connected_channels (youtube_channel_id);
create index if not exists idx_posts_user_id on public.posts (user_id);
create index if not exists idx_posts_channel_id on public.posts (channel_id);
create index if not exists idx_posts_status_schedule_time on public.posts (status, schedule_time);
create index if not exists idx_posts_created_at on public.posts (created_at desc);
create unique index if not exists idx_posts_unique_channel_video on public.posts (channel_id, source_video_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_user_credentials_updated_at on public.user_credentials;
create trigger set_user_credentials_updated_at
before update on public.user_credentials
for each row
execute function public.set_updated_at();

drop trigger if exists set_connected_channels_updated_at on public.connected_channels;
create trigger set_connected_channels_updated_at
before update on public.connected_channels
for each row
execute function public.set_updated_at();

drop trigger if exists set_posts_updated_at on public.posts;
create trigger set_posts_updated_at
before update on public.posts
for each row
execute function public.set_updated_at();
