CREATE TABLE `site_content` (
	`id` integer PRIMARY KEY NOT NULL,
	`draft` text NOT NULL,
	`published` text NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `reward_requests` (
	`id` text PRIMARY KEY NOT NULL,
	`receipt` text NOT NULL,
	`name` text NOT NULL,
	`email` text NOT NULL,
	`category` text NOT NULL,
	`fields` text NOT NULL,
	`submitted_at` text NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL
);
