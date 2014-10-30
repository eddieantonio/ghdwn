# Download Corpora

Download most popular projects for a given language.

 1. Obtain most popular projects list from GitHub.

    Parameters: 
	- LANGAUGE: programming language
	- QUANITY: number of projects

 2. Downloads the tarball of each project.

    a. Untars the project.
    b. Find all files of the given file type; deletes all others.
    c. Syntax checks all the files; prunes files that do not syntax-check.
    d. Moves files to "good" index.

 3. Train corpus based on all of these files.

    a. can do these tasks in parallel.

