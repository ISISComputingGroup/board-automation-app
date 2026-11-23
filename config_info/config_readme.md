# Configuration of this project

This document will detail the configuration requirements needed to run this project which are contained in a `config.ini`.

## Create `config.ini`
1. Copy `blank_config.ini`
2. Rename the copied `blank_config.ini` `config.ini`
3. Ensure that `config.ini` is in your `.gitignore` file if there is a chance you may commit it.
4. Populate the values as per below

## GITHUB.INTERACTION Section
This section covers the interaction with GitHub for graphQL.
### token
- This should be an appropriate GitHub user token, user will need appropriate levels of admin rights in the organisation.
- At present this should be a classic token with repo, admin:org, and project permissions.

### org_name
- This is the name of the organisation to use
- This has been parameterised for ease of reuse of the code in the future

### user_name
- This should be the GitHub username of the user for whom the token was created

### webhook_secret
- This should match the secret used when setting up the app on GitHub

## WWW.INTERACTION Section
This section is the values to use for linking the web server to the web

### host
This is the IP address to use as the host for this website, this will likely map to a web address 
elsewhere

### port
This is the port that is open to the web on the computer it is installed on

## SETTINGS Section

### log_level
This is a value to decide how much information should be included in the log.<br>
All errors will be logged, no matter this value.<br>
If this is set to `developer` all messages are logged, and printed to stdout as well.<br>
If it is set to `all` then informational and debug messages will also be logged.
If it is set to `debug`, or to `info` then only the messages with that same value will be logged 
alongside the errors.

## BOARD.CHECKS Section

### zero_points_labels
It is usual for tickets in sprint boards to require points to gauge both the complexity and effort 
involved. This should be a comma separated list of labels which can be applied to tickets that
would mean they can have a 0 point label. An example entry could be: `Zero Points Allowed, 0 Allowed`

### no_points_labels
It is usual for tickets in sprint boards to require points to gauge both the complexity and effort 
involved. This should be a comma separated list of labels which can be applied to tickets that
would mean they can have no point labels applied. An example entry could be:
`No Points Necessary, Duplicate, Wontfix`

### check_points_labels
If the choice to use the above checks on points needs to be changed, for example due to a switch to
T-Shirt sizing, then setting this to `False` would skip these checks. A setting of `True` will perform
the two checks above related to `zero_points_labels` and `no_points_labels`.

### t_shirt_sizes_in_use
Given the potential variety of T-shirt sizes it is likely that many will just use a subset of the values 
which can be stated using this list. This should be a comma separated list of labels which can be applied 
to tickets. An example entry could be: `size - S,size - M,size - L,size - XL`

### no_t_shirt_size_needed
Not all tickets will come with an effort required, as with the points. This should be a comma separated 
list of labels which can be applied to tickets that would mean they can have no point labels applied. 
An example entry could be:`No Size Necessary, Duplicate, Wontfix`

### check_t_shirt_size_labels
Should T-shirt sizes be used to estimate the amount of work needed in an issue then this entry should be 
set to True. This will ensure that a label matching a value from the `t_shirt_sizes_in_use` list exists 
on any issue that does not have a label from the `no_t_shirt_size_needed` list

### comment_errors
This is a list of labels in use in the project, and a number which indicates the number of days 
since a comment was added after which it can be considered stale. These should be of the following 
format: `label name:n,label name:n`. Please note the lack of spaces around the `:` and `,` 
characters. They will be considered in the order given, and should an error be found, no further 
checks will be undertaken. If a comment error is found this card will not be checked against 
labels.
<br/> 
Note that where labels are not found to match the project fields are currently used for use with
repos that do not have the labels available.

### label_warnings
This is a list of labels in use in the project, and a number which indicates the number of 
days since the label was added on a status change after which it can be considered to be turning 
stale. These should be of the following format: `label name:n,label name:n`. Please note the 
lack of spaces around the `:` and `,` characters. They will be considered in the order given, 
and should a warning be found, no further checks will be undertaken. 
<br/> 
Note that where labels are not found to match the project fields are currently used for use with
repos that do not have the labels available.

### label_errors
This is a list of labels in use in the project, and a number which indicates the number of 
days since the label was added on a status change after which it can be considered stale. 
These should be of the following format: `label name:n,label name:n`. Please note the lack of 
spaces around the `:` and `,` characters. They will be considered in the order given, and should 
an error be found, no further checks will be undertaken. 
<br/> 
Note that where labels are not found to match the project fields are currently used for use with
repos that do not have the labels available.

### allow_unassigned
This is a list of status columns that mean a ticket can be unassigned, if a ticket is in progress
then it should have someone assigned to it

### release_notes_repo
The name of the repo with the release notes to check in, only issues in this repo will be considered

### release_notes_file_path
This is the path within the repo to find the appropriate file, which should be a markdown
file, e.g. "release_notes/ReleaseNotes.md"

### release_notes_branch
The name of the main branch to use for this, no default is provided

### need_notes
This is a list of status columns which need to have release notes as a comma separated list

### notes_exempt
A comma separated list of label names which allow there to be no release notes for the associated issue
