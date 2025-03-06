"""
Caveats:
1. What happens when i want to fork a repo that has the same name as one of my forks?? This script can't handle this issue right now. The function
named fork_exists(name) needs to be modified. 
"""

# you'll need the 'requests' module to run this scripts
# if you want to use virtual environment then you'll need to use #!/path/to/the/virtualenv/bin/python
# at the top of your script

import requests, sys, json

GITHUB_API_URL = r"https://api.github.com"
GITHUB_TOKEN = r"" # Put Your Personal Github Access Token here. Get it from https://github.com/settings/tokens
GITHUB_USERNAME = r"taraqfarhan"  # Put Your GitHub username here

# Headers to include in all requests
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

digits_in_a_num = lambda number: len(str(number))


def get_default_branch(owner, repo): # determine whether the default branch is main or master (both)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repo_info = response.json()
        return repo_info.get("default_branch")
    else: raise Exception(f"Error fetching repo info: {response.json()}")


def repo_and_forks_list():
    repo_list = []
    forks_with_upstream = []
    ultimate_list = []
    
    page = 1
    while True:
        # Fetch repositories owned by the authenticated user
        url = f"{GITHUB_API_URL}/user/repos?affiliation=owner&per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200: raise Exception(f"Error fetching repos: {response.json()}")
        repos = response.json()
        if not repos: break
        
        repo_list.extend([ repo.get('full_name') for repo in repos if repo.get('owner', {}).get('login') == GITHUB_USERNAME ])
    
        for repo in repos:
            if repo.get("fork"): # Check if it's a fork
                repo_full_name = repo["full_name"]  
                # a detailed request for this repo to get the 'parent' field
                details_url = f"{GITHUB_API_URL}/repos/{repo_full_name}"
                details_response = requests.get(details_url, headers=headers)
                if details_response.status_code != 200:
                    print(f"Error fetching details for {repo_full_name}: {details_response.json()}")
                    continue

                elif "parent" in details_response.json():
                    upstream_full_name = details_response.json()["parent"]["full_name"]
                    forks_with_upstream.append((repo_full_name, upstream_full_name)) 
        page += 1
        
        for first, second in forks_with_upstream:
            owner = second.split("/")[0]
            uname = second.split("/")[1]
            name = first.split("/")[1]
            combination = owner, uname, name
            ultimate_list.append(combination)             
        
    return repo_list, forks_with_upstream, ultimate_list


def fork_exists(name):
    url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{name}"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        # print("Fork does not exist.")
        return False
    elif response.status_code == 200:
        # print("Fork exists.")
        return True
    else:
        print("Error checking fork status.")
        return False


def create_fork(owner, urepo_name): 
    url = f"{GITHUB_API_URL}/repos/{owner}/{urepo_name}/forks"
    response = requests.post(url, headers=headers)
    if response.status_code == 202: print(f"Successfully forked the repository: {owner}/{urepo_name}")
    else: print(f"Error creating fork: {response.json()}")
        
        
def get_upstream_commit_sha(owner, urepo_name): 
    default_branch = get_default_branch(owner, urepo_name)
    url = f"{GITHUB_API_URL}/repos/{owner}/{urepo_name}/commits/{default_branch}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        commit_sha = response.json()['sha']
        return commit_sha
    else:
        print("Error fetching the latest upstream commit SHA.")
        return None


def get_fork_commit_sha(repo_name):
    default_branch = get_default_branch(GITHUB_USERNAME, repo_name)
    url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{repo_name}/branches/{default_branch}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        fork_commit_sha = response.json()["commit"]['sha']
        return fork_commit_sha
    else:
        print("Error fetching the latest fork commit SHA.")
        return None


def is_fork_synced(owner, urepo_name): 
    upstream_commit_sha = get_upstream_commit_sha(owner, urepo_name)
    fork_commit_sha = get_fork_commit_sha(urepo_name)
    
    if (upstream_commit_sha) and (fork_commit_sha): return (upstream_commit_sha == fork_commit_sha)
    else: return None


def sync_fork(owner, urepo_name): 
    if is_fork_synced(owner, urepo_name):
        print("Fork is up to date with the upstream.")
    else: 
        print("Fork is behind. Syncing with upstream....")
        sync_url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{urepo_name}/merge-upstream" # check this line again
        payload = { "branch" : f"{get_default_branch(owner, urepo_name)}" } # check this line again
        response = requests.post(sync_url, headers=headers, data=json.dumps(payload))
        if response.status_code in (200, 201): print("Fork has been successfully synced with the upstream.")
        else: print(f"Error syncing the fork: {response.json()}") 


def unsynced_forks_list(ultimate_list):
    unsynced_forks = []
    for owner, uname, name in ultimate_list:
        if not is_fork_synced(owner, uname):
            # print(f"For {GITHUB_USERNAME}/{name} ({owner}/{uname}) the fork is [NOT SYNCED]") 
            unsynced_fork = owner, uname
            unsynced_forks.append(unsynced_fork)
        # else: print(f"For {GITHUB_USERNAME}/{name} ({owner}/{uname}) the fork is [SYNCED]") 

    return unsynced_forks


if __name__ == "__main__":
    try:
        # Create a fork if it doesn't exist else syncs the fork with the upstream (owner/name)
        owner, uname = sys.argv[1:]
        if not fork_exists(uname): create_fork(owner, uname) 
        else: sync_fork(owner, uname)
    except ValueError:
        try:
            option = input("""1. Get the list of all of your repositories.
2. Get the list of all of your forks.
3. Create a new fork. (does nothing if the fork already exists in your repo)
4. Check if a fork is synced with it's upstream or not.
5. Get the list of all the unsynced forks from your repositories.
6. Sync a single fork with it's upstream.
7. Sync all the forks (automatically)
    
What do you want: """)
            if option not in ["1", "2", "3", "4", "5", "6", "7"]: 
                print("Please choose a valid option.")
                quit(1)
            
            elif option in ["3", "4", "6"]:
                data = input("Upstream Repository (username/repo): ").strip()
                owner = data.split("/")[0].strip()
                uname = data.split("/")[1].strip()
                
                if option == "3":
                    create_fork(owner, uname)
                    # if not fork_exists(uname): create_fork(owner, uname)
                    # else: print("This fork already exists in your repo.")
                elif option == "4":
                    if fork_exists(uname): 
                        if (is_fork_synced(owner, uname)): print("The fork is up to date with it's upstream [SYNCED]")
                        else: print("The fork is behind it's upstream [NOT SYNCED]")
                    else: print("This fork doesn't exist in your repo")
                else: # elif option == "6":
                    if fork_exists(uname):
                        if (not is_fork_synced(owner, uname)): sync_fork(owner, uname)
                        else: print("This fork is already synced with it's upstream")
                    else: print("This fork doesn't exist in your repo")
                    
            else: 
                repositories, forks, ultimate_list = repo_and_forks_list()       
                unsynced_forks = unsynced_forks_list(ultimate_list)
            
                if option == "1": 
                    if repositories: 
                        print("All of your Repositories")
                        digits = digits_in_a_num(len(repositories))
                        for index, repo in enumerate(repositories): print(f"{(index+1):{digits}d}. {repo}")
                    else: print("You don't have any repository")

                elif option == "2": 
                    if forks:
                        print("All of your Forks (with their upstreams)")
                        digits = digits_in_a_num(len(forks))
                        for index, info in enumerate(forks): print(f"{(index+1):{digits}d}. {info[0]} ({info[1]})")
                    else: print("No forks were found.")
                            
                elif option == "5": 
                    if (unsynced_forks):
                        print("List of the forks that are not synced")
                        # length = len(unsynced_forks)
                        # for owner, uname in unsynced_forks:
                            # if (length != 1): 
                            #     print(f"{owner}/{uname}, ", end = "")
                            #     length -= 1
                            # else: print(f"{owner}/{uname}")
                        
                        digits = digits_in_a_num(len(unsynced_forks))
                        for index, info in enumerate(unsynced_forks): print(f"{(index+1):{digits}d}. {info[0]}/{info[1]}")
                        
                    else: print("All of your forks are up to date with their upstreams")
                    
                
                elif option == "7":
                    if (len(unsynced_forks) > 0):
                        print(f"Auto syncing.....")
                        for owner, uname in unsynced_forks:
                            print(f"Updating {owner}/{uname}")
                            sync_fork(owner, uname)
                            print()
                        print("All of the forks have been updated with their upstreams")
                    else: print("All of your forks are up to date with their upstreams")

        except KeyboardInterrupt: print("Invalid input [EXITED]")
        except Exception as e: print("An error occurred:", e)